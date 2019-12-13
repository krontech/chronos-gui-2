# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import pyqtProperty, QSize

import chronosGui2.settings as settings
from theme import theme


class Backdrop(QLabel):
	def sizeHint(self):
		return QSize(141, 141)

	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		self.theme = theme('dark') #Gotta provide a default, both clickMarginColor and theme update style and both need to be set.
		self._customStyleSheet = self.styleSheet() #always '' for some reason
		self._showHitRects = showHitRects
		self.refreshStyle()
		
		settings.observe('theme', 'dark', lambda name: (
			setattr(self, 'theme', theme(name)),
			self.refreshStyle(),
		))
		

	def refreshStyle(self):
		if self._showHitRects:
			# Let us see the background grid for editing.
			self.setStyleSheet(f"""
				background: {self.theme.backgroundInEditor};
				border: 4px solid {self.theme.bgBorderInEditor};
				{self._customStyleSheet}
			""")
		else:
			# Full opaque white, don't need that grid now!
			self.setStyleSheet(f"""
				background: {self.theme.background};
				{self._customStyleSheet}
			""")
	
		
	@pyqtProperty(str)
	def customStyleSheet(self):
		return self._customStyleSheet
	
	@customStyleSheet.setter
	def customStyleSheet(self, styleSheet):
		self._customStyleSheet = styleSheet
		self.refreshStyle()