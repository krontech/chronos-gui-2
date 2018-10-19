from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QKeyEvent

from debugger import *; dbg

class FocusablePlugin():
	"""Some behaviour to make focusable widgets work correctly.
	
		Touch and jog wheel have subtly different requirements. Jog wheel can
		focus in to a widget and then have sub-focusses, for example.
	"""
	
	#Subscribe to these signals in the parent class.
	jogWheelDown = pyqtSignal()
	jogWheelUp = pyqtSignal() #fired before click
	jogWheelLowResolutionRotation = pyqtSignal(int, bool) #direction, -1 or +1
	jogWheelHighResolutionRotation = pyqtSignal(int, bool) #direction, -1 or +1
	jogWheelClick = pyqtSignal() #a tap on the jog wheel, cancelled by rotation or long press
	jogWheelLongPress = pyqtSignal() #long press of jog wheel, cancelled by rotation or click
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.isFocussable = True
		try:
			#self.setFocusPolicy(Qt.TabFocus)
			self.setAttribute(Qt.WA_AcceptTouchEvents)
		except Exception as e:
			pass #DNE in in Designer.
	
	#TODO: write useful common functions here, such as "select next".
	#Can maybe use self.parent.window.app.postEvent(…) here, like in main.py?
	
	def injectKeystrokes(self, key, count=1, modifier=Qt.NoModifier):
		"""Inject n keystrokes into the app, to the focused widget."""
		for _ in range(count):
			self.window().app.postEvent(
				self.window().app.focusWidget(), #window._screens[window.currentScreen],
				QKeyEvent(QKeyEvent.KeyPress, key, modifier) )
			self.window().app.postEvent(
				self.window().app.focusWidget(),
				QKeyEvent(QKeyEvent.KeyRelease, key, modifier) )
		
		
	def selectWidget(self, direction):
		"""Select the nth widget in the direction specified.
		
			example: `myWidget.selectWidget(2)` selects the widget
				_after_ the next widget in the focus chain.
		"""
		
		
		nextFn = 'previousInFocusChain' if direction < 0 else 'nextInFocusChain'
		
		widgetToFocus = getattr(self, nextFn)()
		while (not issubclass(type(widgetToFocus), FocusablePlugin) or
				not widgetToFocus.isVisible() or
				widgetToFocus.focusPolicy() not in (Qt.TabFocus, Qt.WheelFocus, Qt.StrongFocus) ):
			widgetToFocus = getattr(widgetToFocus, nextFn)()
		widgetToFocus.setFocus()
		
		# Can't do this for focus, backtab doesn't work reliably when looping
		# over, arrow keys don't work unless compiled for apparently?
		#self.injectKeystrokes(Qt.Key_Tab, count=abs(direction),
		#	modifier=Qt.NoModifier if direction > 0 else Qt.ShiftModifier )
		
		#Show the focus ring here, since this is the function used by the jog
		#wheel to navigate widgets. We don't yet know which widget will be
		#focused next, that will dealt with by a refocus callback on the app.
		self.window().focusRing.show()
		
	
	
	
	#This prevents, among many other things, mouse up from firing for stylesheets.
	#def mouseReleaseEvent(self, event) -> None:
	#	if hasattr(super(), 'mouseReleaseEvent'):
	#		super().mouseReleaseEvent(self, event)
	#	event.ignore() #This doesn't work. :|
	#	print('mouse', event, event.isAccepted())