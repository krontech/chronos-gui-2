# -*- coding: future_fstrings -*-
import os
from string import ascii_uppercase, digits

from PyQt5 import uic, QtCore, QtGui

from chronosGui2.input_panels import KeyboardBase
from button import Button

padding = 10


class KeyboardAlphanumeric(KeyboardBase):
	
	def __init__(self, window):
		super().__init__(window)
		uic.loadUi(os.path.splitext(__file__)[0] + ".ui", self)
		self.move(800-self.width(), 0)
		self.onShow.connect(self.__handleShown)
		
		#We bounce the "done editing" idea through whatever opened us, so if whatever opened us is invalid it has the option of not closing us if it wants to. Is… is this spaghetti logic? I'm so sorry.
		self.uiClose.clicked.connect(lambda: 
			self.opener and self.opener.doneEditing.emit() )
		
		#Wrap "Close" around to "q", so we don't select off the end of the keyboard and close it.
		self.uiClose.jogWheelLowResolutionRotation.disconnect()
		self.uiClose.jogWheelLowResolutionRotation.connect(self.wrapFocusRingSelectionForClose)
		self.uiQ.jogWheelLowResolutionRotation.disconnect()
		self.uiQ.jogWheelLowResolutionRotation.connect(self.wrapFocusRingSelectionForQ)
		
		self.uiShift.pressed.connect(self.toggleCaps)
		
		#Assign keystrokes for each alphanumeric key.
		for key in [getattr(self, f'ui{letter}') for letter in f"{ascii_uppercase}{digits}"]:
			key.pressed.connect((lambda key: #The spare lambda closure captures the key variable, which otherwise is updated in the for loop.
				lambda: self.sendKeystroke(
					getattr(QtCore.Qt, f"Key_{key.text().upper()}") )
			)(key))
		
		#Assign keystrokes for the rest of the keys.
		self.uiDot.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Comma if self.uiShift.keepActiveLook else QtCore.Qt.Key_Period) )
		self.uiBackspace.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Backspace) )
		self.uiSpace.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Space) )
		
		self.uiLeft.pressed.connect(lambda: self.adjustCarat(-1))
		self.uiRight.pressed.connect(lambda: self.adjustCarat(1))
		
		#Keystroke debouncing, because the event fires up to 3 times on one quick press. (Note: Does not occur if press held. I think it's got something to do with redraw and framerate and such, which Qt seems to have a really loose handle on in general.)
		self._lastKey = 0 #If last key = this key, abort and restart the timer. Alternative, use an draw event, that seems to work well in these cases. … we _really_ shouldn't have to do this here.
		self._clearLastKeyTimer = QtCore.QTimer()
		self._clearLastKeyTimer.timeout.connect(lambda:
			setattr(self, '_lastKey', 0) )
		self._clearLastKeyTimer.setInterval(200) 
	
	def __handleShown(self, options):
		"""Set to fire when keyboard is shown.
		
			options is like:
				{
					'focus': False,
					'hints': /,\\,\\\\,test,toast,🦇,﷽,ﷺ,
					'opener': <line_edit.LineEdit object at 0x46155cb0>,
				}
			"""
		
		if not options["hints"]:
			self.uiSuggestionBar.hide()
			inputGeometry = QtCore.QRect(0, padding, self.uiKeyPanel.width(), self.uiKeyPanel.height())
			self.uiKeyPanel.setGeometry(inputGeometry)
			inputGeometry.setHeight(inputGeometry.height() + padding) #This is like the opposite of a good API. It is minimally expressive.
			self.setGeometry(inputGeometry)
		else:
			self.uiSuggestionBar.show()
			inputGeometry = QtCore.QRect(0, self.uiSuggestionBar.height(), self.uiKeyPanel.width(), self.uiKeyPanel.height())
			self.uiKeyPanel.setGeometry(inputGeometry)
			inputGeometry.setHeight(inputGeometry.height() + self.uiSuggestionBar.height()) #The lack of padding here is worrying, but works. I think something in the input panel is covering for it.
			self.setGeometry(inputGeometry)
			self.uiSuggestionBarLayout.parentWidget().raise_()
			
			for i in range(self.uiSuggestionBarLayout.count()): #Clear the existing widgets.
				self.uiSuggestionBarLayout.itemAt(i).widget().deleteLater()
			
			for hint in options["hints"]:
				print('adding hint', hint)
				hintButton = Button(self.uiSuggestionBarLayout.parentWidget())
				hintButton.setText(hint)
				hintButton.setFocusPolicy(
					QtCore.Qt.StrongFocus
					if options["focus"]
					else QtCore.Qt.NoFocus )
				hintButton.clicked.connect(
					#We can't inject keystrokes directly, it seems - `self.sendKeystroke(ord(hint[0]), hint) )` is broken?
					(lambda hint: lambda: options['opener'].insert(hint))(hint) ) #Bind hint from for loop.
				hintButton.clickMarginLeft = 0
				hintButton.clickMarginRight = 0
				hintButton.clickMarginTop = hintButton.half
				hintButton.clickMarginBottom = 0
				hintButton.setCustomStyleSheet("Button { border-left-width: 0px; }") #We can't set a border of -1, which is what we actually need, so we remove one border from our buttons to maintain the 1px-wide lines.
				self.uiSuggestionBarLayout.addWidget(hintButton)
				hintButton.show()
			
			
		
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
		
		self.uiDot.setText(',' if self.uiShift.keepActiveLook else '.')
		for keycap in [getattr(self, f'ui{letter}') for letter in ascii_uppercase]:
			keycap.setText(getattr(keycap.text(), 
				'upper' if self.uiShift.keepActiveLook else 'lower')())
	
	def sendKeystroke(self, code, text=''): #Can this use QKeySequence?
		if self._lastKey == code:
			print(f'swallowing key #{code}')
			return
		self._clearLastKeyTimer.start()
		self._lastKey = code
		
		print(f'emitting key #{code}')
		
		#The QLineEdit backing widget for text input relies on the text value of the key event, so we need to synthesize a text for the event to take effect.
		try:
			eventText = text or chr(code)
		except ValueError:
			eventText = ''
		
		#Incoming codes are always upper-case.
		if not self.uiShift.keepActiveLook:
			eventText = eventText.lower()
			
		
		#If we're typing a capital, unshift after typing it.
		if self.uiShift.keepActiveLook and code >= QtCore.Qt.Key_A and code <= QtCore.Qt.Key_Z:
			self.toggleCaps()
		
		for action in [QtGui.QKeyEvent.KeyPress, QtGui.QKeyEvent.KeyRelease]:
			self.parent().app.sendEvent(
				self.opener,
				QtGui.QKeyEvent(
					action,
					code,
					QtCore.Qt.ShiftModifier if self.uiShift.keepActiveLook else QtCore.Qt.NoModifier,
					eventText #This is the magic to actually get the event to take effect for non-backspace keys.
				)
			)
	
	
	def adjustCarat(self, direction):
		self.opener.cursorForward(False, direction)
		
		#Reset cursor flash time, so it's always visible when we're moving it.
		cursorFlashTime = self.window().app.cursorFlashTime()
		self.window().app.setCursorFlashTime(-1)
		self.window().app.setCursorFlashTime(cursorFlashTime)