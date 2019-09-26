# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtProperty, QSize

from debugger import *; dbg


class InteractiveVideoArea(QWidget):
	def sizeHint(self):
		return QSize(141, 141)

	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		self._customStyleSheet = self.styleSheet() #always '' for some reason
		self._showHitRects = showHitRects
		
		self.refreshStyle()
		
		if showHitRects:
			#Needed to make black background show up in Designer.
			#Doesn't work. Just check it manually in Designer. :/
			self.setAutoFillBackground(True)
		

	def refreshStyle(self):
		if self._showHitRects:
			# Let us see the background grid for editing.
			self.setStyleSheet(f"""
				background: rgba(0,0,0,128);
				border: 4px solid black;
				{self._customStyleSheet}
			""")
		else:
			# Full opaque white, don't need that grid now!
			self.setStyleSheet(f"""
				background: transparent;
				{self._customStyleSheet}
			""")
	
		
	@pyqtProperty(str)
	def customStyleSheet(self):
		return self._customStyleSheet
	
	@customStyleSheet.setter
	def customStyleSheet(self, styleSheet):
		self._customStyleSheet = styleSheet
		self.refreshStyle()