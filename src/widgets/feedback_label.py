from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize

from debugger import *; dbg


class FeedbackLabel(QLabel):
	"""A flashy little error label. 
		
		Text is usually set by calling showMsg(…).
	"""
	
	#I'd like to make the error message flash, but that's a bit of a "stretch goal" right now.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.showError('«error message will go here»')
		
		if not showHitRects:
			self.hide()
			


	def sizeHint(self):
		return QSize(141, 21)
	
	def showError(self, message: str) -> None:
		"""Show an error message. Use .hide() when the condition has passed."""
		
		self.setStyleSheet(f"""
			font-size: 14px;
			background: transparent;
			color: #c80000;
		""")
		
		self.setText(message)
		self.show()
	
	def showMessage(self, message: str) -> None:
		"""Show a feedback message. Use .hide() when the condition has passed."""
		
		self.setStyleSheet(f"""
			font-size: 14px;
			background: transparent;
			color: #000000;
		""")
		
		self.setText(message)
		self.show()
	