from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg
from widgets.touch_margin_plugin import TouchMarginPlugin


class FocusRing(QLabel):
	"""A movable focus ring, to indicate what the jog wheel is pointing at.
	
		This widget is added to a screen when the screen is created. It is
		not placable in Qt Designer.
	"""
	
	padding = 10 #This can't seem to be assigned via CSS.
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.setAttribute(Qt.WA_TransparentForMouseEvents)
		self.setFocusPolicy(Qt.NoFocus)
		
		self.setStyleSheet(f"""
			border: 2px solid #1D6262;
			background: rgba(196,196,255,32);
			border-radius: {self.padding}px;
		""")
		self.setGeometry(-999,-999, 0,0)
	
	
	def focusOn(self, widget):
		"""Move focus to a widget."""
		xy = widget.parentWidget().mapToGlobal(widget.pos())
		wh = widget.size()
		if hasattr(widget, '_clickMarginLeft'):
			xy += QPoint(
				widget._clickMarginLeft, 
				widget._clickMarginTop,
			)*10 - QPoint(self.padding, self.padding)
			wh -= QSize(
				widget._clickMarginLeft + widget._clickMarginRight, 
				widget._clickMarginBottom + widget._clickMarginTop,
			)*10 - QSize(self.padding, self.padding)*2
		self.window().focusRing.setGeometry(QRect(xy, wh))
	
	def focusIn(self):
		"""Move focus to a widget."""
		print('focus in')
	
	def focusOut(self):
		"""Move focus to a widget."""
		print('focus out')