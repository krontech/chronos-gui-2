from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg

from touch_margin_plugin import TouchMarginPlugin, MarginWidth


class SpinBox(QSpinBox, TouchMarginPlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, inEditor=False):
		super().__init__(parent, inEditor=inEditor)
		self.refreshStyle()


	def sizeHint(self):
		return QSize(181, 81)
	
	
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
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				/* App style. Use margin to provide further click area outside the visual button. */
				font-size: 16px;
				background: white;
				border: 1px solid black;
				border-left-color: rgb(50,50,50);
				border-top-color: rgb(50,50,50); /* Add a subtle 3d-ness until we figure out drop-shadows. */
				
				/* Add some touch space so this widget is easier to press. */
				margin-left: {self.clickMarginLeft*10}px;
				margin-right: {self.clickMarginRight*10}px;
				margin-top: {self.clickMarginTop*10}px;
				margin-bottom: {self.clickMarginBottom*10}px;
			""" + self.originalStyleSheet())