from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg


class Label(QLabel):
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
		return QSize(141, 41)