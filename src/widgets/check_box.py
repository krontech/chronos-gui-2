# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt
from PyQt5.QtWidgets import QCheckBox

from debugger import *; dbg
import settings
import logging; log = logging.getLogger('Chronos.gui')

from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from direct_api_link_plugin import DirectAPILinkPlugin
from focusable_plugin import FocusablePlugin


class CheckBox(QCheckBox, TouchMarginPlugin, DirectAPILinkPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	jogWheelRotationCancelsClick = False #Widget doesn't use rotation. Ignore it.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		
		self.theme = ''
		self._clickMarginRight = MarginWidth.none
		self.clickMarginColor = f"rgba({randint(128, 255)}, {randint(0, 32)}, {randint(128, 255)}, {randint(32,96)})"
		
		settings.observe('theme', 'dark', lambda theme: (
			setattr(self, 'theme', theme),
			self.refreshStyle(),
		))
		
		self.setMouseTracking(True)
		
		self.jogWheelLowResolutionRotation.connect(lambda delta, pressed: 
			not pressed and self.selectWidget(delta) )
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Space))
		
		# Focus ring effect.
		self.jogWheelDown.connect(lambda: self.window().focusRing.focusIn(amount=.25)) #Small click effect.
		self.jogWheelUp.connect(lambda: self.window().focusRing.focusOut())
		self.jogWheelLongPress.connect(lambda: self.window().focusRing.focusOut(speed=.04))
	
	
	def sizeHint(self):
		return QSize(181, 81)
	
	
	def mousePressEvent(self, ev):
		"""Use the full area of the widget to toggle the checkbox, not just the visual checkbox and text."""
		if ev.button() == Qt.LeftButton:
			ev.accept()
			self.toggle()
		else:
			ev.ignore()
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				CheckBox {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					font-size: 16px;
					background: rgba(255,255,255,127); /* The background is drawn under the button borders, so they are opaque if the background is opaque. */
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
				
				CheckBox::indicator:checked {{
					image: url(../../assets/images/checkbox-checked.svg.png);
				}}
				CheckBox::indicator:unchecked {{
					image: url(../../assets/images/checkbox-unchecked.svg.png);
				}}
				
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				CheckBox {{
					/* App style. Use margin to provide further click area outside the visual button. */
					font-size: 16px;
					color: {'white' if self.theme == 'dark' else 'black'};
					background-color: {'#333' if self.theme == 'dark' else 'white'};
					
					/* Add some touch space so this widget is easier to press. */
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
				}}
				
				CheckBox::indicator:checked {{
					image: url(assets/images/checkbox-checked.svg.png);
				}}
				CheckBox::indicator:unchecked {{
					image: url(assets/images/checkbox-unchecked.svg.png);
				}}
			""" + self.originalStyleSheet())