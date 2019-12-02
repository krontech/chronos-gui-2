# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg
import settings
from theme import theme

from show_paint_rect_plugin import ShowPaintRectsPlugin


class Label(ShowPaintRectsPlugin, QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.baseStyleSheet = self.styleSheet()
		settings.observe('theme', 'dark', lambda name:
			self.setStyleSheet(f"""
				font-size: 16px;
				background: transparent;
				color: {theme(name).text};
			""" + self.baseStyleSheet )
		)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('text')


	def sizeHint(self):
		return QSize(141, 21)