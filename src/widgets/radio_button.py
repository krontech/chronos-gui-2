from random import randint

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth


class RadioButton(QRadioButton, TouchMarginPlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def sizeHint(self):
		return QSize(181, 81)
	
	
	def __init__(self, parent=None, inEditor=False):
		super().__init__(parent, inEditor=inEditor)
		self.clickMarginColor = f"rgba({randint(128, 255)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
	
	
	def mousePressEvent(self, ev):
		"""Use the full area of the widget to toggle the radio button, not just the visual checkbox and text."""
		if ev.button() == Qt.LeftButton:
			ev.accept()
			self.toggle()
		else:
			ev.ignore()
	
	
	def refreshStyle(self):
		if self.inEditor:
			self.setStyleSheet(f"""
				RadioButton {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					font-size: 16px;
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
				
				RadioButton::indicator {{
					width: 18px;
					height: 18px;
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				RadioButton {{
					/* App style. Use margin to provide further click area outside the visual button. */
					font-size: 16px;
					padding-left: 10px;
					
					/* Add some touch space so this widget is easier to press. */
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
				}}
				
				RadioButton::indicator {{
					width: 18px;
					height: 18px;
				}}
			""" + self.originalStyleSheet())