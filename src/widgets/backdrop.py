from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import pyqtProperty, QSize

from debugger import *; dbg


class Backdrop(QLabel):
	def sizeHint(self):
		return QSize(141, 141)

	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		self._customStyleSheet = self.styleSheet() #always '' for some reason
		self._showHitRects = showHitRects
		self.refreshStyle()

	def refreshStyle(self):
		if self._showHitRects:
			# Let us see the background grid for editing.
			self.setStyleSheet(f"""
				background: rgba(255,255,255,128);
				border: 4px solid white;
				{self._customStyleSheet}
			""")
		else:
			# Full opaque white, don't need that grid now!
			self.setStyleSheet(f"""
				background: white;
				{self._customStyleSheet}
			""")
	
		
	@pyqtProperty(str)
	def customStyleSheet(self):
		return self._customStyleSheet
	
	@customStyleSheet.setter
	def customStyleSheet(self, styleSheet):
		self._customStyleSheet = styleSheet
		self.refreshStyle()