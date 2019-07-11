# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QLineEdit

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from direct_api_link_plugin import DirectAPILinkPlugin
from focusable_plugin import FocusablePlugin


class LineEdit(QLineEdit, TouchMarginPlugin, DirectAPILinkPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, showHitRects=False):
		self.keepActiveLook = False

		super().__init__(parent, showHitRects=showHitRects)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('')
		
		self.setCursorMoveStyle(Qt.LogicalMoveStyle) #Left moves left, right moves right. Defaults is right arrow key moves left under rtl writing systems.
			
		self.clickMarginColor = f"rgba({randint(128, 255)}, {randint(64, 128)}, {randint(0, 32)}, {randint(32,96)})"
		
		self.inputMode = '' #Set to empty, 'jogWheel', or 'touch'. Used for defocus event handling behaviour.
		
		self.jogWheelLowResolutionRotation.connect(self.handleJogWheelRotation)
		self.jogWheelClick.connect(self.jogWheelClicked)
		
		self.touchEnd.connect(self.editTapped)
		
		self.doneEditing.connect(self.doneEditingCallback)
		
		###
		### TODO: Add an event filter to get clicked events. (We can't 
		###       use focus events because the jog wheel does that when
		###       it rolls over an input.) Bring up the input panel.
		###
		
		#When we tap an input, we deselect selected text. But we want to
		#select all text. So, select it again after we've tapped it. Note:
		#This only applies if the keyboard hasn't bumped the text out of the
		#way first.
		self.selectAllTimer = QtCore.QTimer()
		self.selectAllTimer.timeout.connect(self.selectAll)
		self.selectAllTimer.setSingleShot(True)
	
	def sizeHint(self):
		return QSize(361, 81)
		
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
				LineEdit {{
					font-size: 16px;
					background: rgba(255,255,255,127); /* The background is drawn under the button borders, so they are opaque if the background is opaque. */
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				LineEdit {{
					/* App style. Use margin to provide further click area outside the visual button. */
					font-size: 16px;
					background: white;
					border: 1px solid black;
					border-left-color: rgb(50,50,50);
					border-top-color: rgb(50,50,50); /* Add a subtle 3d-ness until we figure out drop-shadows. */
					
					/* Add some touch space so this widget is easier to press. */
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
				}}
			""" + self.originalStyleSheet())
	
	def jogWheelClicked(self):
		if self.window().focusRing.isFocussedIn:
			self.window().focusRing.focusOut()
			self.doneEditing.emit()
		else:
			self.inputMode = 'jogWheel'
			self.window().app.window.showInput('alphanumeric', focus=True)
		
		self.selectAll()
		self.selectAllTimer.start(16)
	
	def editTapped(self):
		if self.inputMode == 'touch':
			return
		
		self.inputMode = 'touch'
		self.window().app.window.showInput('alphanumeric', focus=False)
		self.window().focusRing.focusIn()
		
		self.selectAll()
		self.selectAllTimer.start(16)
	
	def doneEditingCallback(self):
		self.inputMode = ''
		self.window().app.window.hideInput()
	
	def handleJogWheelRotation(self, delta, pressed):
		if self.inputMode:
			if pressed:
				self.cursorWordForward(False) if delta > 0 else self.cursorWordBackward(False)
			else:
				self.cursorForward(False, delta)
			
			#An important detail - reset the cursor flash so it's always visible while moving, so we can see where we have moved it to.
			cursorFlashTime = self.window().app.cursorFlashTime()
			self.window().app.setCursorFlashTime(-1)
			self.window().app.setCursorFlashTime(cursorFlashTime)
		else:
			self.selectWidget(delta)
	
	def paintEvent(self, event):
		super().paintEvent(event)
		
		#If we're in jog wheel mode, this input does not show the cursor because
		#focus is on the keyboard. To work around this issue, we draw our own
		#cursor. It's a cheap hack, though, so it doesn't blink or adjust kerning.
		if self.inputMode == 'jogWheel':
			rect = self.cursorRect()
			half = rect.width()//2
			rect.translate(+half, 0)
			rect.setWidth(1)
			QPainter(self).fillRect(rect, Qt.SolidPattern)