from PyQt5.QtCore import *

from random import randint

from debugger import dbg, brk; dbg, brk


class MarginWidth:
		none, half, full = range(3)


class TouchMarginPlugin(MarginWidth):
	"""Add 20px margins to a Qt Widget.
	
	This makes it much easier to press the widget on a touchscreen.
	
	Notes:
	
		- Use self.originalStyleSheet() instead of self.stylesheet(). The
		stylesheet is somewhat dynamic now, as the style changes when the
		margins are changed. (note: This could - and perhaps should - be
		switched to a getter/setter so it's less intrusive, but since I don't
		think we'll be doing a lot of work at the level where that would
		matter it's better to keep it clearer and use another identifier.)
		
	"""
	
	Q_ENUMS(MarginWidth)
	
	def __init__(self, inEditor=False):
		self.inEditor = inEditor
		self._originalStyleSheet = self.styleSheet()
		
		# Invisible margin to make clicking on buttons easier. When placing
		# buttons, it's important to make sure the margin isn't on top of other
		# elements.
		self._clickMarginLeft = MarginWidth.full
		self._clickMarginRight = MarginWidth.full
		self._clickMarginTop = MarginWidth.full
		self._clickMarginBottom = MarginWidth.full
		
		# self._clickMarginColor = f"rgba({randint(0, 32)}, {randint(0, 32)}, {randint(128, 255)}, {randint(32,96)})"
		colour = randint(100, 227)
		self._clickMarginColor = f"rgba({colour}, {colour}, {colour}, {randint(32,96)})"
		
		
	def refreshStyle(self):
		"""Implement this to call self.setStyleSheet(str) with a recomputed stylesheet."""
		raise NotImplementedError
	
	
	def setOriginalStyleSheet(self, sheet):
		self._originalStyleSheet = sheet
	
	def originalStyleSheet(self):
		return self._originalStyleSheet

	@pyqtProperty(MarginWidth)
	def clickMarginLeft(self):
		return self._clickMarginLeft
		
	@clickMarginLeft.setter
	def clickMarginLeftSetter(self, state):
		self._clickMarginLeft = state
		self.refreshStyle()
	
		
	@pyqtProperty(MarginWidth)
	def clickMarginRight(self):
		return self._clickMarginRight
		
	@clickMarginRight.setter
	def clickMarginRightSetter(self, state):
		self._clickMarginRight = state
		self.refreshStyle()
	
	
	@pyqtProperty(MarginWidth)
	def clickMarginTop(self):
		return self._clickMarginTop
		
	@clickMarginTop.setter
	def clickMarginTopSetter(self, state):
		self._clickMarginTop = state
		self.refreshStyle()
	
	
	@pyqtProperty(MarginWidth)
	def clickMarginBottom(self):
		return self._clickMarginBottom
		
	@clickMarginBottom.setter
	def clickMarginBottomSetter(self, state):
		self._clickMarginBottom = state
		self.refreshStyle()
	
	
	def clickMarginColorGetter(self):
		return self._clickMarginColor
	
	def clickMarginColorSetter(self, state):
		self._clickMarginColor = state
		self.refreshStyle()
		
	clickMarginColor = property(clickMarginColorGetter, clickMarginColorSetter)