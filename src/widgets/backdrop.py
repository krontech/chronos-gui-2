from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg


class Backdrop(QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		if showHitRects:
			# Let us see the background grid for editing.
			self.setStyleSheet(f"""
				background: rgba(255,255,255,128);
				border: 4px solid white;
			""" + self.styleSheet())
		else:
			# Full opaque white, don't need that grid now!
			self.setStyleSheet(f"""
				background: white;
			""" + self.styleSheet())


	def sizeHint(self):
		return QSize(141, 141)