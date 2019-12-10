# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

import chronosGui2.settings as settings
from theme import theme


class Subheader(QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.baseStyleSheet = self.styleSheet()
		settings.observe('theme', 'dark', lambda name:
			self.setStyleSheet(f"""
				font-size: 18px;
				background: transparent;
				color: {theme(name).text};
			""" + self.baseStyleSheet )
		)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('Subheader')


	def sizeHint(self):
		return QSize(241, 21)