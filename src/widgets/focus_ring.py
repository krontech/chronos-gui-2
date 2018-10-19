from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QPoint, QSize, QRect

from debugger import *; dbg


class FocusRing(QLabel):
	"""A movable focus ring, to indicate what the jog wheel is pointing at.
	
		This widget is added to a screen when the screen is created. It is
		not placable in Qt Designer.
	"""
	
	unfocussedPadding = 10 #This can't seem to be assigned via CSS.
	focussedPadding = 2
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.currentPadding = self.unfocussedPadding
		
		self.setAttribute(Qt.WA_TransparentForMouseEvents)
		self.setFocusPolicy(Qt.NoFocus)
		
		self.setStyleSheet(f"""
			border: 2px solid #1D6262;
			background: rgba(196,196,255,32);
			border-radius: {self.currentPadding}px;
		""")
		self.hide()
	
	
	def focusOn(self, widget):
		"""Move focus to a widget."""
		xy = widget.parentWidget().mapToGlobal(widget.pos())
		wh = widget.size()
		
		#Subtract the invisible touch margins, *usually* supplied by TouchMarginPlugin.
		try:
			margins = widget.touchMargins()
		except AttributeError:
			margins = None
		
		if margins:
			xy += QPoint(
				margins["left"], 
				margins["top"],
			) - QPoint(self.currentPadding, self.currentPadding)
			wh -= QSize(
				margins["left"] + margins["right"], 
				margins["bottom"] + margins["top"],
			) - QSize(self.currentPadding, self.currentPadding)*2
			
		self.window().focusRing.setGeometry(QRect(xy, wh))
	
	def focusIn(self):
		"""Move focus to a widget."""
		print('focus in')
	
	def focusOut(self):
		"""Move focus to a widget."""
		print('focus out')