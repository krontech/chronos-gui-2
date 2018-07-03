from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import dbg, brk; dbg, brk

from random import randint


def dump(val):
	print(val)
	return val


class Button(QPushButton):
	
	class MarginWidth:
		none, half, full = range(3)
		
	Q_ENUMS(MarginWidth)
	
	none, half, full = range(3) #Must duplicate MarginWidth because QT Designer produces files which try to load it off the base Button.
		
	
	def __init__(self, parent=None, inEditor=False):
		super(Button, self).__init__(parent)
		
		self.inEditor = inEditor
		self.originalStyleSheet = self.styleSheet()
		
		# Invisible margin to make clicking on buttons easier. When placing
		# buttons, it's important to make sure the margin isn't on top of other
		# elements.
		self._clickMarginLeft = Button.MarginWidth.full
		self._clickMarginRight = Button.MarginWidth.full
		self._clickMarginTop = Button.MarginWidth.full
		self._clickMarginBottom = Button.MarginWidth.full
		
		self._clickMarginColor = f"rgba({randint(0, 32)}, {randint(0, 32)}, {randint(128, 255)}, {randint(32,96)})"
		
		self.refreshStyle()
		
	def refreshStyle(self):
		if self.inEditor:
			self.setStyleSheet(f"""
				/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
				font-size: 16px;
				background: white;
				
				/* use borders instead of margins so we can see what we're doing */
				border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self._clickMarginColor};
				border-right:  {self.clickMarginRight  * 10 + 1}px solid {self._clickMarginColor};
				border-top:    {self.clickMarginTop    * 10 + 1}px solid {self._clickMarginColor};
				border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self._clickMarginColor};
			""" + self.originalStyleSheet)
		else:
			self.setStyleSheet(f"""
				/* App style. Use margin to provide further click area outside the visual button. */
				font-size: 16px;
				background: white;
				border: 1px solid black;
				border-left-color: rgb(50,50,50);
				border-top-color: rgb(50,50,50); /* Add a subtle 3d-ness until we figure out drop-shadows. */
				
				/* calculate margins */
				margin-left: {self.clickMarginLeft*10}px;
				margin-right: {self.clickMarginRight*10}px;
				margin-top: {self.clickMarginTop*10}px;
				margin-bottom: {self.clickMarginBottom*10}px;
			""" + self.originalStyleSheet)
		
	def sizeHint(self):
		return QSize(181, 81)


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