# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg
from show_paint_rect_plugin import ShowPaintRectsPlugin


class Label(ShowPaintRectsPlugin, QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.setStyleSheet(f"""
			font-size: 16px;
			background: transparent;
		""" + self.styleSheet())
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('text')


	def sizeHint(self):
		return QSize(141, 21)