# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt
from PyQt5.QtWidgets import QDoubleSpinBox, QLineEdit

from debugger import *; dbg
from signal_tap import signalTap

from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from direct_api_link_plugin import DirectAPILinkPlugin
from focusable_plugin import FocusablePlugin
from si_units_plugin import SIUnitsPlugin


JOG_WHEEL_MOVES_CURSOR = False

class DecimalSpinBox(QDoubleSpinBox, TouchMarginPlugin, DirectAPILinkPlugin, FocusablePlugin, SIUnitsPlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		
		self.setCorrectionMode(self.CorrectToNearestValue)
		
		self.clickMarginColor = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(128, 255)}, {randint(32,96)})"
		
		self.isFocused = False
		self.inputMode = '' #Set to empty, 'jogWheel', or 'touch'. Used for defocus event handling behaviour.
		
		self.jogWheelClick.connect(self.jogWheelClicked)
		self.jogWheelLowResolutionRotation.connect(self.onLowResRotate)
		
		self.touchEnd.connect(self.editTapped)
		self.findChild(QLineEdit).installEventFilter(self) #Make touchEnd fire when our sub-edit is tapped. Otherwise, the keyboard only opens when the touch margins are tapped. The event filter itself is inherited from FocusablePlugin.
		self.doneEditing.connect(self.doneEditingCallback)
		
		#When we tap an input, we deselect selected text. But we want to
		#select all text. So, select it again after we've tapped it. Note:
		#This only applies if the keyboard hasn't bumped the text out of the
		#way first.
		self.selectAllTimer = QtCore.QTimer()
		self.selectAllTimer.timeout.connect(self.selectAll)
		self.selectAllTimer.setSingleShot(True)
		
		valueChangedTap = signalTap(lambda val:
			(val * self.unitValue[self.siUnit],) )
		self.valueChanged.connect(valueChangedTap.emit)
		self.valueChanged = valueChangedTap
	
	def sizeHint(self):
		return QSize(201, 81)
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				DecimalSpinBox {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					font-size: 16px;
					border: 1px solid black;
					padding-right: 0px;
					padding-left: 10px;
					background: rgba(255,255,255,127); /* The background is drawn under the button borders, so they are opaque if the background is opaque. */
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
				DecimalSpinBox:disabled {{ 
					color: #969696;
				}}
				DecimalSpinBox::up-button, DecimalSpinBox::down-button {{
					width: 0px; /*These buttons just take up room. We have a jog wheel for them.*/
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				DecimalSpinBox {{ 
					font-size: 16px;
					border: 1px solid black;
					padding-right: 0px;
					padding-left: 10px;
					background: white;
					
					/* Add some touch space so this widget is easier to press. */
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
				}}
				DecimalSpinBox:disabled {{ 
					color: #969696;
				}}
				DecimalSpinBox::up-button, DecimalSpinBox::down-button {{
					width: 0px; /*These buttons just take up room. We have a jog wheel for them.*/
				}}
			""" + self.originalStyleSheet())
	
	
	def onLowResRotate(self, delta, pressed):
		if self.isFocused or self.inputMode == 'touch':
			if self.inputMode == 'touch' and JOG_WHEEL_MOVES_CURSOR:
				if pressed:
					if delta > 0: #TODO: Make this, and spin_box, and line_edit, select instead of moving by word.
						self.findChild(QLineEdit).cursorWordForward(False)
					else:
						self.findChild(QLineEdit).cursorWordBackward(False)
				else:
					self.findChild(QLineEdit).cursorForward(False, delta)
				
				#An important detail - reset the cursor flash so it's always visible while moving, so we can see where we have moved it to.
				cursorFlashTime = self.window().app.cursorFlashTime()
				self.window().app.setCursorFlashTime(-1)
				self.window().app.setCursorFlashTime(cursorFlashTime)
			else:
				if pressed:
					self.injectKeystrokes(
						Qt.Key_PageUp if delta > 0 else Qt.Key_PageDown,
						count=abs(delta) )
				else:
					self.injectKeystrokes(
						Qt.Key_Up if delta > 0 else Qt.Key_Down,
						count=abs(delta) )
		else:
			if pressed:
				self.injectKeystrokes(
					Qt.Key_PageUp if delta > 0 else Qt.Key_PageDown,
					count=abs(delta) )
			else:
				self.selectWidget(delta)
	
	
	def jogWheelClicked(self):
		self.isFocused = not self.isFocused
		
		if self.isFocused:
			self.inputMode = 'jogWheel'
			self.window().focusRing.focusIn()
		else:
			self.inputMode = ''
			self.window().focusRing.focusOut()
	
	
	def editTapped(self):
		if self.inputMode == 'touch':
			return
		
		self.inputMode = 'touch'
		self.isFocused = True
		self.window().app.window.showInput(self,
			'numeric_with_units' if self.units else 'numeric_without_units', 
			focus=False,
		)
		self.window().focusRing.focusIn()
		
		self.selectAll()
		self.selectAllTimer.start(16)
	
	
	def doneEditingCallback(self):
		log.debug(f'DONE EDITING {self.objectName()}')
		self.inputMode = ''
		self.isFocused = False
		self.window().app.window.hideInput()
	
	
	def value(self):
		return self.realValue(super().value)
	def setValue(self, val):
		return self.setRealValue(super().setValue, val)
	
	def minimum(self):
		return self.realMinimum(super().minimum)
	def setMinimum(self, val):
		return self.setRealMinimum(super().setMinimum, val)
	
	def maximum(self):
		return self.realMaximum(super().maximum)
	def setMaximum(self, val):
		return self.setRealMaximum(super().setMaximum, val)
	