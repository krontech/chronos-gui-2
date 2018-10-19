from PyQt5.QtCore import Q_ENUMS, pyqtProperty

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
	
	def __init__(self, *args, showHitRects=False, **kwargs):
		super().__init__(*args, **kwargs)
		self.showHitRects = showHitRects
		#self._customStyleSheet = self.styleSheet() #This is always blank during init, don't know why. Set up another custom property to cover for it, since those do seem to have a story for retrieval.
		
		# Invisible margin to make clicking on buttons easier. When placing
		# buttons, it's important to make sure the margin isn't on top of other
		# elements.
		self._clickMarginLeft = MarginWidth.full
		self._clickMarginRight = MarginWidth.full
		self._clickMarginTop = MarginWidth.full
		self._clickMarginBottom = MarginWidth.full
		self._customStyleSheet = ''
		
		# self._clickMarginColor = f"rgba({randint(0, 32)}, {randint(0, 32)}, {randint(128, 255)}, {randint(32,96)})"
		color = randint(100, 227)
		self._clickMarginColor = f"rgba({color}, {color}, {color}, {randint(32,96)})"
		
		
	def refreshStyle(self):
		"""Implement this to call self.setStyleSheet(str) with a recomputed stylesheet."""
		raise NotImplementedError
	
	
	def setOriginalStyleSheet(self, sheet):
		self._customStyleSheet = sheet
	
	def originalStyleSheet(self):
		return self._customStyleSheet
	
	
	def touchMargins(self):
		return {
			"top": self._clickMarginTop * 10,
			"left": self._clickMarginLeft * 10,
			"bottom": self._clickMarginBottom * 10,
			"right": self._clickMarginRight * 10,
		}
	
	
	@pyqtProperty(MarginWidth)
	def clickMarginLeft(self):
		return self._clickMarginLeft
		
	@clickMarginLeft.setter
	def clickMarginLeftSetter(self, state):
		# We can't adjust the x position of our object to compensate for this, unfortunately, since there's no way to tell if the object is being set via menu or if it's being initialized.
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
	
	
	@property
	def clickMarginColor(self):
		return self._clickMarginColor
	
	@clickMarginColor.setter
	def clickMarginColor(self, state):
		self._clickMarginColor = state
		self.refreshStyle()
		
	@pyqtProperty(str)
	def customStyleSheet(self):
		return self._customStyleSheet
	
	@customStyleSheet.setter
	def customStyleSheet(self, styleSheet):
		self._customStyleSheet = styleSheet
		self.refreshStyle()