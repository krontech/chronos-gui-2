# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg


class Subheader(QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.setStyleSheet(f"""
			font-size: 17px; /*Effectively 16pt bold. 🙄 15.5pt is better, but renders really small in Qt Designer.*/
			background: transparent; /*Don't mess with this, it affects font width.*/
		""" + self.styleSheet())
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('Subheader')


	def sizeHint(self):
		return QSize(241, 21)