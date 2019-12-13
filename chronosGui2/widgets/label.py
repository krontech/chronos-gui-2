# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

import chronosGui2.settings as settings
from chronosGui2 import delay
from theme import theme

from show_paint_rect_plugin import ShowPaintRectsPlugin


class Label(ShowPaintRectsPlugin, QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		def initialiseStyleSheet():
			self.baseStyleSheet = self.styleSheet()
			settings.observe('theme', 'dark', lambda name:
				self.setStyleSheet(f"""
					font-size: 16px;
					background: transparent;
					color: {theme(name).text};
				""" + self.baseStyleSheet )
			)
		delay(self, 0, initialiseStyleSheet) #Delay until after init is done and stylesheet is set. NFI why this isn't handled by super().__init__.
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('text')


	def sizeHint(self):
		return QSize(141, 21)