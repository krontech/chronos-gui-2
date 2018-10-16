from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent

class FocusablePlugin():
	"""Some behaviour to make focussable widgets work correctly.
	
		Touch and jog wheel have subtly different requirements. Jog wheel can
		focus in to a widget and then have sub-focusses, for example.
	"""
	
	#Subscribe to these signals in the parent class.
	jogWheelDown = pyqtSignal()
	jogWheelUp = pyqtSignal() #fired before click
	jogWheelRotate = pyqtSignal(int) #direction, -1 or +1
	jogWheelClick = pyqtSignal() #a tap on the jog wheel, cancelled by rotation or long press
	jogWheelLongPress = pyqtSignal() #long press of jog wheel, cancelled by rotation or click
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.isFocussable = True
		#self.setFocusPolicy(Qt.TabFocus)
		self.setAttribute(Qt.WA_AcceptTouchEvents)
		
		self.jogWheelDown.connect(lambda: print(self, 'jogWheelDown'))
		self.jogWheelUp.connect(lambda: print(self, 'jogWheelUp'))
		self.jogWheelRotate.connect(lambda: print(self, 'jogWheelRotate'))
		self.jogWheelClick.connect(lambda: print(self, 'jogWheelClick'))
		self.jogWheelLongPress.connect(lambda: print(self, 'jogWheelLongPress'))
	
	#TODO: write useful common functions here, such as "select next".
	#Can maybe use self.parent.window.app.postEvent(…) here, like in main.py?
	
	def injectSelect(self, *, state):
		app = self.parent.window.app
		if state == "down":
			keyAction = QKeyEvent.KeyPress
		elif state == "up":
			keyAction = QKeyEvent.KeyRelease
		else:
			raise ValueError(f'Select key state, "{state}", must be "down" or "up".')
		
		app.postEvent(
			app.focusWidget(), #window._screens[window.currentScreen],
			QKeyEvent(keyAction, Qt.Key_Select, Qt.NoModifier)
		)
		
	
	#This prevents, among many other things, mouse up from firing for stylesheets.
	#def mouseReleaseEvent(self, event) -> None:
	#	if hasattr(super(), 'mouseReleaseEvent'):
	#		super().mouseReleaseEvent(self, event)
	#	event.ignore() #This doesn't work. :|
	#	print('mouse', event, event.isAccepted())