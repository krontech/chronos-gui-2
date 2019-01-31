# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt
from PyQt5.QtWidgets import QPushButton

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from focusable_plugin import FocusablePlugin


class Button(QPushButton, TouchMarginPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	jogWheelRotationCancelsClick = False #Widget doesn't use rotation. Ignore it.
	
	def __init__(self, parent=None, showHitRects=False):
		self.keepActiveLook = False
		
		super().__init__(parent, showHitRects=showHitRects)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('Button')
			
		self.clickMarginColor = f"rgba({randint(0, 32)}, {randint(0, 32)}, {randint(128, 255)}, {randint(32,96)})"
		
		self.jogWheelLowResolutionRotation.connect(lambda delta, pressed: 
			not pressed and self.selectWidget(delta) )
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Space))
		
		# Focus ring effect.
		self.jogWheelDown.connect(lambda: self.window().focusRing.focusIn(amount=.25)) #Small click effect.
		self.jogWheelUp.connect(lambda: self.window().focusRing.focusOut())
		self.jogWheelLongPress.connect(lambda: self.window().focusRing.focusOut(speed=.04))
		
		# Jog wheel highlight button on click effect.
		self.jogWheelDown.connect(lambda: (self.__setattr__('keepActiveLook', True), self.refreshStyle()))
		self.jogWheelUp.connect(lambda: (self.__setattr__('keepActiveLook', False), self.refreshStyle()))
		self.jogWheelLongPress.connect(lambda: (self.__setattr__('keepActiveLook', False), self.refreshStyle()))
		self.jogWheelCancel.connect(lambda: (self.__setattr__('keepActiveLook', False), self.refreshStyle()))
		
	
	def sizeHint(self):
		return QSize(181, 81)
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
				Button {{
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
				Button {{
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
				
				Button{'' if self.keepActiveLook else ':pressed'} {{
					border-color: rgb(50,50,50);
					border-top-color: black;
					border-left-color: black;
					background: rgb(240,240,240);
				}}
			""" + self.originalStyleSheet())