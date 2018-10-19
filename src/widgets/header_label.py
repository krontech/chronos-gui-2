from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg


class HeaderLabel(QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.setStyleSheet(f"""
			font-size: 21px;
			background: transparent;
		""" + self.styleSheet())
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('Header')


	def sizeHint(self):
		return QSize(241, 31)