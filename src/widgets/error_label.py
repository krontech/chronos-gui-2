from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg


class ErrorLabel(QLabel):
	"""A flashy little error label. 
		
		Text is usually set by calling showMsg(…).
	"""
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.setStyleSheet(f"""
			font-size: 14px;
			background: transparent;
			color: #c80000;
		""" + self.styleSheet())
		
		if not showHitRects:
			self.hide()
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('«error message will go here»')
			
		#I'd like to make the error message flash, but that's a "stretch goal" right now.


	def sizeHint(self):
		return QSize(141, 21)
	
	def showMessage(self, message: str) -> None:
		"""Show an error message. Use .hide() when the condition has passed."""
		
		self.setText(message)
		self.show()