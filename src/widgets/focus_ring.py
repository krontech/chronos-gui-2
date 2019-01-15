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
		self._paddingMinMultiplier = 0.
		self._paddingMaxMultiplier = 1.
		self._currentPadding = self.unfocussedPadding
		self.isFocussedIn = False
		self._focussedOn = None
		
		self.focusInOutTimer = QtCore.QTimer()
		self.focusInOutTimer.timeout.connect(self._updateFocusRingPadding)
		self.focusInOutTimer.setInterval(16)
		
		self.refreshStyleSheet(self._currentPadding)
		self.hide()
	
	
	def focusOn(self, widget):
		"""Move focus to a widget."""
		
		
		self._focussedOn = widget
		
		#Allow combobox dropdown menus to not be ringed, since they have the highlight which fulfills the purpose.
		if getattr(widget, 'hideFocusRingFocus', False):
			self.setGeometry(-9999,-9999,10,10) #Just move the focus ring off-screen if it's supposed to be hidden. That way, it doesn't mess with hidden/shown status.
			return
		
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
		
		self.setGeometry(QRect(xy, wh))
		self.raise_() #Make focus ring appear above keyboard.
	
	
	def _updateFocusRingPadding(self):
		# This construct, with associated timers and class state variables, reimplements an
		#	`animate(self._currentPadding, [unfocussedPadding, focussedPadding], frames(5))` function.
		
		self._paddingMultiplier += self._paddingMultiplierDelta
		if self._paddingMultiplier < self._paddingMinMultiplier:
			self._paddingMultiplier = self._paddingMinMultiplier
			self.focusInOutTimer.stop()
		elif self._paddingMultiplier > self._paddingMaxMultiplier:
			self._paddingMultiplier = self._paddingMaxMultiplier
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
	
	def refocus(self):
		self._focussedOn and self.focusOn(self._focussedOn)
	
	
	def focusIn(self, *, immediate: bool = False, speed: float = .75, amount: float = 1.):
		"""Tighten focus on the selected widget.
			
			------------------------------------------------------------
			To focus on a widget, use focusOn(widget). This function,
			focusIn, makes the focus ring smaller around the widget to
			indicate it's "got input". For example, when you focus in on
			a slider, the focus ring tightens around the handle and
			moving the jog wheel moves the handle instead of the focus
			ring. To indicate release focus, use focusOut.
			
			Note that the widget currently focussed is entirely
			responsible for choosing what happens when input is given.
			Calling focusIn or focusOut doesn't affect the actual logic.
			
			Keywords:
				immediate: if True, do not animate change. Equivalent
					to speed=1.0.
				speed: How fast to animate. Animation is 1 unit long,
					and speed is the delta each frame. Speed need not
					divide evenly into the animation length.
				amount: How much of the animation to play. 1.0 plays all
					the animation, and 0.0 plays none of the animation.
					So, setting amount to 0.25, we play 1/4th of the
					full animation and then stop."""
		
		self._paddingMultiplierDelta = -1. if immediate else -speed
		self._paddingMinMultiplier = 1.0 - amount
		self._updateFocusRingPadding()
		immediate or self.focusInOutTimer.isActive() or self.focusInOutTimer.start()
		self.isFocussedIn = True
	
	def focusOut(self, *, immediate: bool = False, speed: float = .75, amount: float = 1.):
		"""Loosen focus on the selected widget.
			
			------------------------------------------------------------
			To focus on a widget, use focusOn(widget). This function,
			focusOut, is the opposite of focusIn. It indicates release
			of focus. See focusIn for more details!
			
			Keywords:
				immediate: if True, do not animate change. Equivalent
					to speed=1.0.
				speed: How fast to animate. Animation is 1 unit long,
					and speed is the delta each frame. Speed need not
					divide evenly into the animation length.
				amount: How much of the animation to play. 1.0 plays all
					the animation, and 0.0 plays none of the animation.
					So, setting amount to 0.25, we play 1/4th of the
					full animation and then stop."""
		
		self._paddingMultiplierDelta = 1. if immediate else speed
		self._paddingMaxMultiplier = amount
		self._updateFocusRingPadding()
		immediate or self.focusInOutTimer.isActive() or self.focusInOutTimer.start()
		self.isFocussedIn = False