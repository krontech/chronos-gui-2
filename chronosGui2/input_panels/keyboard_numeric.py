# -*- coding: future_fstrings -*-
import os
from string import digits

from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtWidgets import QDoubleSpinBox, QLineEdit

from chronosGui2.input_panels import KeyboardBase
from chronosGui2.generated.keyboard_numeric_nounits import Ui_uiKeyboardNumericNoUnits
from chronosGui2.generated.keyboard_numeric_units_lh import Ui_uiKeyboardNumericUnitsLH

padding = 10

class KeyboardNumericBase(KeyboardBase):
	def __init__(self, window):
		super().__init__(window)
		self.setupUi(self) # This is provided by one of the concrete types below.
		
		# Panel init.
		self.move(800-self.width(), 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.setUpSelectionWrap()
		
		self.onShow.connect(self.__handleShown)
		
		#We bounce the "done editing" idea through whatever opened us, so if whatever opened us is invalid it has the option of not closing us if it wants to. Is… is this spaghetti logic? I'm so sorry.
		self.uiClose.clicked.connect(lambda: self.opener and (
			self.opener.interpretText(), #Old intermediate input can remain if still selected, explicitly interpret when keyboard closed.
			self.opener.doneEditing.emit(),
		))
		
		#Assign keystrokes for each alphanumeric key.
		for key in [getattr(self, f'ui{digit}') for digit in digits]:
			key.pressed.connect((lambda key: #The spare lambda closure captures the key variable, which otherwise is updated in the for loop.
				lambda: self.sendKeystroke(
					getattr(QtCore.Qt, f"Key_{key.text()}") )
			)(key))
		
		#Assign keystrokes for the rest of the keys.
		self.uiDot.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Period) )
		self.uiBackspaceNarrow.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Backspace) )
		self.uiBackspaceWide.pressed.connect(lambda: 
			self.sendKeystroke(QtCore.Qt.Key_Backspace) )
		
		self.uiLeft.pressed.connect(lambda: self.adjustCarat(-1))
		self.uiRight.pressed.connect(lambda: self.adjustCarat(1))
	
	def setUpSelectionWrap(self):
		#Wrap "Close" around to "q", so we don't select off the end of the keyboard and close it.
		self.uiClose.jogWheelLowResolutionRotation.disconnect()
		self.uiClose.jogWheelLowResolutionRotation.connect(self.wrapFocusRingSelectionForClose)
		self.ui7.jogWheelLowResolutionRotation.disconnect()
		self.ui7.jogWheelLowResolutionRotation.connect(self.wrapFocusRingSelectionFor7)
	
	def wrapFocusRingSelectionForClose(self, delta, pressed):
		if delta < 0:
			return not pressed and self.uiClose.selectWidget(delta)
		else:
			self.ui7.setFocus()
	
	def wrapFocusRingSelectionFor7(self, delta, pressed):
		if delta > 0:
			return not pressed and self.ui7.selectWidget(delta)
		else:
			self.uiClose.setFocus()
	
	
	def __handleShown(self, options):
		#Show or hide the dot key by putting a wide backspace key over it.
		self.uiBackspaceWide.setVisible(
			not issubclass(type(self.opener), QDoubleSpinBox) )
		
		inputGeometry = QtCore.QRect(padding, 0, self.uiKeyPanel.width(), self.uiKeyPanel.height())
		inputGeometry.setHeight(inputGeometry.height() + padding) #This is like the opposite of a good API. It is minimally expressive.
		
		#Calculate content position.
		
		openerGeometry = options["opener"].geometry() #Three syntaxes for "give me the member data".
		contentsGeometry = self.parentWidget().screenContents.geometry()
		screenGeometry = self.parentWidget().geometry()
		
		availableArea = QtCore.QRect(0,0, 
			screenGeometry.width() - inputGeometry.width(), screenGeometry.height())
		
		targetHorizontalLocationForInput = availableArea.width()//2 - openerGeometry.width()//2 #Calculate ideal side of *widget*, since we can't set widget center.
		idealContentsDeltaToCenter = targetHorizontalLocationForInput - openerGeometry.left()
		
		#Clamp the screen delta so it never leaves part of the screen undrawn.
		if contentsGeometry.left() + idealContentsDeltaToCenter >= screenGeometry.left():
			contentsDeltaToCenter = screenGeometry.left() #We're already as low as we can go. Go no lower.
		elif contentsGeometry.right() + idealContentsDeltaToCenter <= availableArea.right():
			contentsDeltaToCenter = availableArea.width() - screenGeometry.width() + padding #Go as high as we can go, less padding so the fade still works. ;)
		else:
			contentsDeltaToCenter = idealContentsDeltaToCenter
		contentsGeometry.moveLeft(
			0+contentsDeltaToCenter)
		self.parentWidget().screenContents.setGeometry(contentsGeometry)
	
	
	def sendKeystroke(self, code):
		print(f'emitting key #{code}')
		
		#The QLineEdit backing widget for text input relies on the text value of the key event, so we need to synthesize a text for the event to take effect.
		try:
			eventText = chr(code)
		except ValueError:
			eventText = ''
		
		for action in [QtGui.QKeyEvent.KeyPress, QtGui.QKeyEvent.KeyRelease]:
			self.parent().app.sendEvent(
				self.opener,
				QtGui.QKeyEvent(
					action,
					code,
					QtCore.Qt.NoModifier,
					eventText #This is the magic to actually get the event to take effect for non-backspace keys.
				),
			)
	
	
	def adjustCarat(self, direction):
		self.opener.findChild(QLineEdit).cursorForward(False, direction)
		
		#Reset cursor flash time, so it's always visible when we're moving it.
		cursorFlashTime = self.window().app.cursorFlashTime()
		self.window().app.setCursorFlashTime(-1)
		self.window().app.setCursorFlashTime(cursorFlashTime)


class KeyboardNumericWithoutUnits(KeyboardNumericBase, Ui_uiKeyboardNumericNoUnits):
	"""A numeric keyboard with no unit buttons."""
	pass

class KeyboardNumericWithUnits(KeyboardNumericBase, Ui_uiKeyboardNumericUnitsLH):
	"""A numeric keyboard with unit buttons.
		
		This works with the """

	def __init__(self, window):
		super().__init__(window)
		
		self.onShow.connect(self.__handleShown)
		
		self.uiMega .toggled.connect(self.unitToggled(0, self.uiMega ))
		self.uiKilo .toggled.connect(self.unitToggled(1, self.uiKilo ))
		self.uiMilli.toggled.connect(self.unitToggled(2, self.uiMilli))
		self.uiMicro.toggled.connect(self.unitToggled(3, self.uiMicro))
		
	def unitToggled(self, unitIndex, button):
		def unitToggledCallback(isChecked):
			min_ = self.opener.minimum()
			max_ = self.opener.maximum()
			val_ = self.opener.value()
			
			buttons = [self.uiMega, self.uiKilo, self.uiMilli, self.uiMicro]
			if isChecked: #Wait. I have created radio buttons. … This is easier than reskinning the actual things, I guess. :p
				self.opener.unit = self.opener.unitList[unitIndex]
				for otherButton in buttons:
					if otherButton != button:
						otherButton.setChecked(False)
			else:
				if self.opener.unit == self.opener.unitList[unitIndex]:
					self.opener.unit = self.opener.unitsPostfix
					for i in range(len(self.opener.unitList)): #Check the right button.
						if self.opener.unitList[i] == self.opener.unit:
							buttons[i].setChecked(True)
							break
			
			#Set the min/max/value to take into account the new unit.
			self.opener.setMinimum(min_)
			self.opener.setMaximum(max_)
			self.opener.setValue(val_)
		return unitToggledCallback
	
	
	def __handleShown(self, options):
		"""When shown, load the units the input has specified for use.
			
			Hide any unused unit buttons."""
		
		#Check for the appropriate number of units in the units list. Do not use this units keyboard if there is only one unit, it should be implicit then. And on the other extreme, we just don't have room for more than 4 units in the current design. :p
		assert 2 <= len(self.opener.unitList) <= 4, f"Expected between 2 and 4 units for {self.opener.objectName()} ({self.opener}), got {self.opener.unitList} which is {len(self.opener.unitList)} long."
		
		buttons = [self.uiMega, self.uiKilo, self.uiMilli, self.uiMicro]
		for buttonIndex in range(len(buttons)):
			try:
				buttons[buttonIndex].setText(self.opener.unitList[buttonIndex])
				buttons[buttonIndex].show()
			except IndexError: #Not that many units.
				buttons[buttonIndex].hide()