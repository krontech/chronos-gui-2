from string import ascii_uppercase, digits

from PyQt5 import uic, QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal

from debugger import *; dbg

padding = 10


class KeyboardAlphanumeric(QtWidgets.QWidget):
	onShow = pyqtSignal('QVariantMap')
	onHide = pyqtSignal()
	
	def __init__(self, window):
		super().__init__()
		
		uic.loadUi("src/input_panels/keyboard_alphanumeric.ui", self)
		
		# Panel init.
		self.move(800-self.width(), 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.onShow.connect(self.__handleShown)
		self.onHide.connect(self.__handleHide)
		
		self.opener = None
		
		#We bounce the "done editing" idea through whatever opened us, so if whatever opened us is invalid it has the option of not closing us if it wants to. Is… is this spaghetti logic? I'm so sorry.
		self.uiClose.clicked.connect(lambda: 
			self.opener and self.opener.doneEditing.emit() )
		
		#Wrap "Close" around to "q", so we don't select off the end of the keyboard and close it.
		self.uiClose.jogWheelLowResolutionRotation.disconnect()
		self.uiClose.jogWheelLowResolutionRotation.connect(self.wrapFocusRingSelectionForClose)
		self.uiQ.jogWheelLowResolutionRotation.disconnect()
		self.uiQ.jogWheelLowResolutionRotation.connect(self.wrapFocusRingSelectionForQ)
		
		self.refocusFocusRingTimer = QtCore.QTimer()
		self.refocusFocusRingTimer.timeout.connect(lambda: 
			self.window().focusRing.refocus() )
		self.refocusFocusRingTimer.setSingleShot(True)
		
		self.uiShift.pressed.connect(self.toggleCaps)
		
		#Assign keystrokes for each alphanumeric key.
		for key in [getattr(self, f'ui{letter}') for letter in f"{ascii_uppercase}{digits}"]:
			key.pressed.connect((lambda key: #The spare lambda closure captures the key variable, which otherwise is updated in the for loop.
				lambda: self.sendKeystroke(
					getattr(QtCore.Qt, f"Key_{key.text().upper()}") )
			)(key))
		
		#Assign keystrokes for the rest of the keys.
		self.uiDot.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Period) )
		self.uiBackspace.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Backspace) )
		self.uiSpace.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Space) )
		
		self.uiLeft.pressed.connect(lambda: self.adjustCarat(-1))
		self.uiRight.pressed.connect(lambda: self.adjustCarat(1))
	
	def __handleShown(self, options):
		#eg, {'focus': False, 'hints': [], 'opener': <line_edit.LineEdit object at 0x46155cb0>}
		self.show()
		self.opener = options["opener"]
		
		#Calculate keyboard height and position.
		
		#If there are no hints, hide the suggestion bar. Calculate the heigh of the panel, 
		if not options["hints"]:
			self.uiSuggestionBar.hide()
			inputGeometry = QtCore.QRect(0,padding, self.uiKeyPanel.width(), self.uiKeyPanel.height())
			self.uiKeyPanel.setGeometry(inputGeometry)
			inputGeometry.setHeight(inputGeometry.height() + padding) #This is like the opposite of a good API. It is minimally expressive.
			self.setGeometry(inputGeometry)
		else:
			self.uiSuggestionBar.show()
			inputGeometry = QtCore.QRect(0,self.uiSuggestionBar.height(), self.uiKeyPanel.width(), self.uiKeyPanel.height())
			self.uiKeyPanel.setGeometry(inputGeometry)
			inputGeometry.setHeight(inputGeometry.height() + self.uiSuggestionBar.height() + padding)
			self.setGeometry(inputGeometry)
			print('SUGGESTION BAR NOT IMPLEMENTED (check it works correctly with tap VS jog wheel focus modes)')
		
		self.setGeometry(0, self.parentWidget().height() - self.height(), self.width(), self.height())
		
		
		#Calculate content position.
		
		openerGeometry = options["opener"].geometry() #Three syntaxes for "give me the member data".
		contentsGeometry = self.parentWidget().screenContents.geometry()
		screenGeometry = self.parentWidget().geometry()
		
		availableArea = QtCore.QRect(0,0, 
			screenGeometry.width(), screenGeometry.height() - inputGeometry.height() )
		
		targetVerticalLocationForInput = availableArea.height()//2 - openerGeometry.height()//2 #Calculate ideal top of *widget*, since we can't set widget center.
		idealContentsDeltaToCenter = targetVerticalLocationForInput - openerGeometry.top()
		
		#Clamp the screen delta so it never leaves part of the screen undrawn.
		if contentsGeometry.top() + idealContentsDeltaToCenter >= screenGeometry.top():
			contentsDeltaToCenter = screenGeometry.top() #We're already as low as we can go. Go no lower.
		elif contentsGeometry.bottom() + idealContentsDeltaToCenter <= availableArea.bottom():
			contentsDeltaToCenter = availableArea.height() - screenGeometry.height() + padding #Go as high as we can go, less padding so the fade still works. ;)
		else:
			contentsDeltaToCenter = idealContentsDeltaToCenter
		contentsGeometry.moveTop(
			0+contentsDeltaToCenter)
		self.parentWidget().screenContents.setGeometry(contentsGeometry)
		
		###
		###
		### TODO: See how animation looks.
		###
		###
		
		
		#Set button focus policy.
		
		for pane in self.children():
			for widget in pane.children():
				if type(widget) is QtWidgets.QHBoxLayout:
					for widget in widget.children():
						widget.setFocusPolicy(
							QtCore.Qt.StrongFocus 
							if options["focus"] 
							else QtCore.Qt.NoFocus
						)
				else:
					widget.setFocusPolicy(
						QtCore.Qt.StrongFocus 
						if options["focus"] 
						else QtCore.Qt.NoFocus
					)
		
		if options["focus"]:
			self.uiClose.setFocus()
			self.window().focusRing.focusOut(immediate=True)
		else:
			self.window().focusRing.refocus()
		
		self.parent().app.focusChanged.connect(self.__handleFocusChange)
	
	def __handleHide(self):
		"""Implement the hide command communicated to us.
			
			Note: May be called several times if multiple conditions would close.
			"""
		
		#Debounce.
		if self.isHidden():
			return
		
		self.hide()
		
		contentsGeometry = self.parentWidget().screenContents.geometry()
		contentsGeometry.moveTop(0)
		self.parentWidget().screenContents.setGeometry(contentsGeometry)
		
		try:
			self.parent().app.focusChanged.disconnect(self.__handleFocusChange)
		except TypeError:
			print('Warning: __handleFocusChange for alphanumeric keyboard not connected.')
			pass
		
		#Refresh focus ring position or focus on the thing that opened us, since the previously focussed button just disappeared.
		self.opener.setFocus()
		self.refocusFocusRingTimer.start(16) #Position of opener changes asynchronously.
			
	
	def __handleFocusChange(self, old, new):
		focussedOnInputOrKeyboard = new == self.opener or True in [new in child.children() for child in self.children()]
		if not focussedOnInputOrKeyboard:
			self.opener.doneEditing.emit()
	
	
	def wrapFocusRingSelectionForClose(self, delta, pressed):
		if delta < 0:
			return not pressed and self.uiClose.selectWidget(delta)
		else:
			self.uiQ.setFocus()
	
	def wrapFocusRingSelectionForQ(self, delta, pressed):
		if delta > 0:
			return not pressed and self.uiQ.selectWidget(delta)
		else:
			self.uiClose.setFocus()
	
	def toggleCaps(self):
		self.uiShift.keepActiveLook = not self.uiShift.keepActiveLook
		self.uiShift.refreshStyle()
		
		for keycap in [getattr(self, f'ui{letter}') for letter in ascii_uppercase]:
			keycap.setText(getattr(keycap.text(), 
				'upper' if self.uiShift.keepActiveLook else 'lower')())
	
	def sendKeystroke(self, code):
		print(f'emitting key #{code}')
		
		#The QLineEdit backing widget for text input relies on the text value of the key event, so we need to synthesize a text for the event to take effect.
		try:
			eventText = chr(code)
		except ValueError:
			eventText = ''
		
		#Incoming codes are always upper-case.
		if not self.uiShift.keepActiveLook:
			eventText = eventText.lower()
			
		
		#If we're typing a capital, unshift after typing it.
		if self.uiShift.keepActiveLook and code >= QtCore.Qt.Key_A and code <= QtCore.Qt.Key_Z:
			self.toggleCaps()
		
		self.parent().app.sendEvent(
			self.opener,
			QtGui.QKeyEvent(
				QtGui.QKeyEvent.KeyPress,
				code,
				QtCore.Qt.ShiftModifier if self.uiShift.keepActiveLook else QtCore.Qt.NoModifier,
				eventText #This is the magic to actually get the event to take effect for non-backspace keys.
			)
		)
		self.parent().app.sendEvent(
			self.opener,
			QtGui.QKeyEvent(
				QtGui.QKeyEvent.KeyRelease,
				code,
				QtCore.Qt.ShiftModifier if self.uiShift.keepActiveLook else QtCore.Qt.NoModifier,
				eventText
			)
		)
	
	def adjustCarat(self, direction):
		self.opener.cursorForward(False, direction)
		
		#Reset cursor flash time, so it's always visible when we're moving it.
		cursorFlashTime = self.window().app.cursorFlashTime()
		self.window().app.setCursorFlashTime(-1)
		self.window().app.setCursorFlashTime(cursorFlashTime)