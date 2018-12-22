from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QPoint, QSize, QRect

from debugger import *; dbg


class FocusRing(QLabel):
	"""A movable focus ring, to indicate what the jog wheel is pointing at.
	
		This widget is added to a screen when the screen is created. It is
		not placable in Qt Designer.
	"""
	
	unfocussedPadding = 10 #This can't seem to be assigned via CSS.
	focussedPadding = 4
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.setAttribute(Qt.WA_TransparentForMouseEvents)
		self.setFocusPolicy(Qt.NoFocus)
		
		self._paddingMultiplier = 1
		self._paddingMultiplierDelta = .1 #Set later.
		self._currentPadding = self.unfocussedPadding
		self.isFocussedIn = False
		self._focussedOn = None
		
		self.focusInOutTimer = QtCore.QTimer()
		self.focusInOutTimer.timeout.connect(self.updateFocusRingPadding)
		self.focusInOutTimer.setInterval(16)
		
		self.refreshStyleSheet(self._currentPadding)
		self.hide()
	
	
	def focusOn(self, widget):
		"""Move focus to a widget."""
		
		self._focussedOn = widget
		
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
			) - QPoint(self._currentPadding, self._currentPadding)
			wh -= QSize(
				margins["left"] + margins["right"], 
				margins["bottom"] + margins["top"],
			) - QSize(self._currentPadding, self._currentPadding)*2
			
		self.window().focusRing.setGeometry(QRect(xy, wh))
	
	
	def updateFocusRingPadding(self):
		# This construct, with associated timers and class state variables, reimplements an
		#	`animate(self._currentPadding, [unfocussedPadding, focussedPadding], frames(5))` function.
		
		self._paddingMultiplier += self._paddingMultiplierDelta
		if self._paddingMultiplier < 0:
			self._paddingMultiplier = 0
			self.focusInOutTimer.stop()
		elif self._paddingMultiplier > 1:
			self._paddingMultiplier = 1
			self.focusInOutTimer.stop()
		
		totalPaddingDifference = self.unfocussedPadding - self.focussedPadding
		self._currentPadding = self.focussedPadding + (totalPaddingDifference * self._paddingMultiplier)
		self.refreshStyleSheet(self.unfocussedPadding * self._paddingMultiplier)
	
	def refreshStyleSheet(self, ringPadding: int):
		self.setStyleSheet(f"""
			border: 2px solid #1D6262;
			background: rgba(196,196,255,32);
			border-radius: {ringPadding}px;
			widget-animation-duration: 1000;
		""")
		
		self._focussedOn and self.focusOn(self._focussedOn)
	
	
	def focusIn(self, *, immediate=False):
		"""Move focus to a widget."""
		self._paddingMultiplierDelta = -1. if immediate else -.75
		self.updateFocusRingPadding()
		immediate or self.focusInOutTimer.isActive() or self.focusInOutTimer.start()
		self.isFocussedIn = True
	
	def focusOut(self, *, immediate=False):
		"""Move focus to a widget."""
		self._paddingMultiplierDelta = 1. if immediate else .75
		self.updateFocusRingPadding()
		immediate or self.focusInOutTimer.isActive() or self.focusInOutTimer.start()
		self.isFocussedIn = False