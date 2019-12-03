# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt, pyqtProperty
from PyQt5.QtWidgets import QPushButton

from debugger import *; dbg
import settings
from show_paint_rect_plugin import ShowPaintRectsPlugin
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from focusable_plugin import FocusablePlugin
from theme import theme


class Button(ShowPaintRectsPlugin, TouchMarginPlugin, FocusablePlugin, QPushButton):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	jogWheelRotationCancelsClick = False #Widget doesn't use rotation. Ignore it.
	
	def __init__(self, parent=None, showHitRects=False):
		self.keepActiveLook = False
		self._fake_disability = False
		self._hideBorder = None
		
		super().__init__(parent, showHitRects=showHitRects)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('Button')
		
		self.theme = theme('dark') #Gotta provide a default, both clickMarginColor and theme update style and both need to be set.
		self.clickMarginColor = f"rgba({randint(0, 32)}, {randint(0, 32)}, {randint(128, 255)}, {randint(32,96)})"
		
		settings.observe('theme', 'dark', lambda name: (
			setattr(self, 'theme', theme(name)),
			self.refreshStyle(),
		))
		
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
					background: {self.theme.baseInEditor}; /* The background is drawn under the button borders, so they are opaque if the background is opaque. We need them to be transparent because we can't see borders under borders otherwise. */
					color: {self.theme.text};
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				/* App style. Use margin to provide further click area outside the visual button. */
				Button {{
					font-size: 16px;
					color: {self.theme.dimText if self.fake_disability else self.theme.text};
					background-color: {self.theme.background if self.hideBorder else self.theme.base};
					
					border: 1px solid {'transparent' if self.hideBorder else self.theme.border};
					
					/* Add some touch space so this widget is easier to press. */
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
				}}
				
				Button{'' if self.keepActiveLook or self.fake_disability else ':pressed'} {{ /*Look active if faking disability; gives a radio-button-esque feel to disabled buttons. ¯\\_(ツ)_/¯ */
					background: {self.theme.baseActive};
				}}
			""" + self.originalStyleSheet())
	
	@property
	def fake_disability(self):
		"""Look greyed-out but still allow selection.
		
			Don't actually disable the button because that turns off selection. Event
			callbacks must check for this manually, since the button will still work
			fine."""
		
		return self._fake_disability
		
	@fake_disability.setter
	def fake_disability(self, disabled: bool):
		self._fake_disability = disabled
		self.refreshStyle()
	
	
	@pyqtProperty(bool)
	def hideBorder(self):
		return False if self._hideBorder is None else self._hideBorder
		
	@hideBorder.setter
	def hideBorder(self, hide):
		self._hideBorder = hide
		self.refreshStyle()