# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg
import settings
from theme import theme


class HeaderLabel(QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.baseStyleSheet = self.styleSheet()
		settings.observe('theme', 'dark', lambda name:
			self.setStyleSheet(f"""
				font-size: 24px;
				background: transparent;
				color: {theme(name).text};
			""" + self.baseStyleSheet )
		)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('Header')


	def sizeHint(self):
		return QSize(241, 31)