# -*- coding: future_fstrings -*-

from math import copysign

from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication

from debugger import *; dbg

class FocusablePlugin():
	"""Some behaviour to make focusable widgets work correctly.
	
		Touch and jog wheel have subtly different requirements. Jog wheel can
		focus in to a widget and then have sub-focusses, for example. Keyboard
		(software input) has additional data requirements such as units and
		desired input type.
	"""
	
	# Normally, rotating the encoder knob cancels a click event. This is so
	# that pressing and rotating, which fires
	# jogWheel(?:Low|High)ResolutionRotation events, doesn't trigger the click
	# handlers when you just wanted rotation events. Generally, you would only
	# set this to False for a class of widget which doesn't respond to jog
	# wheel rotation events.
	jogWheelRotationCancelsClick = True
	
	#Subscribe to these signals in the parent class.
	jogWheelDown = pyqtSignal()
	jogWheelUp = pyqtSignal() #fired before click
	jogWheelLowResolutionRotation = pyqtSignal(int, bool) #direction, -1 or +1; jog wheel is depressed
	jogWheelHighResolutionRotation = pyqtSignal(int, bool) #direction, -1 or +1; jog wheel is depressed
	jogWheelClick = pyqtSignal() #a tap on the jog wheel, cancelled by rotation or long press
	jogWheelLongPress = pyqtSignal() #long press of jog wheel, cancelled by rotation or click
	jogWheelCancel = pyqtSignal() #click/long-press is aborted by jog wheel rotation
	
	touchStart = pyqtSignal() #fired when you click or touch the input
	touchEnd = pyqtSignal()
	
	doneEditing = pyqtSignal() #Fired when the keyboard input should close.
	
	#Specify the widget property "units", on numeric inputs, to provide a list of units to choose from. It is recommended to stick to 4, since that's how many unit buttons are on the numeric keyboard. Units can be scrolled with the jog wheel.
	unitList = ['y', 'z', 'a', 'f', 'p', 'n', 'µ', 'm', '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
	knownUnits = { #Map of units to their multipliers. eg, k = kilo = ×1000. Or µs = microseconds = ×0.000001. Usually queried with unit[:1], because something like mV or ms both have the same common numerical multiplier. [0] is not used because it fails on "".
		suffix: 10**((index-8)*3) for index, suffix in enumerate(unitList) #Position 8 is neutral, 'no unit'.
	}
	knownUnits['s'] = 1 #seconds
	knownUnits['V'] = 1 #volts
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.isFocussable = True
		try:
			#self.setFocusPolicy(Qt.TabFocus)
			self.setAttribute(Qt.WA_AcceptTouchEvents)
		except Exception:
			pass #DNE in in Designer.
		
		self.jogWheelIndex = 1
		self.editMode = 'touch' #vs 'jogwheel'
		
		if hasattr(self, 'units'): #The 
			self.originalPrefix = self.prefix()
			self.originalSuffix = self.suffix()
			assert self.suffix()[:1] in self.availableUnits(), f'{self.window().objectName()}.{self.objectName()}: Suffix "{self.suffix()}" unit "{self.suffix()[:1]}" not found in {self.availableUnits()}. (List via "units" widget property set to "{self.units}.")' #Test slice, might not have first character if unit is "".
		
		self.installEventFilter(self)
	
	#TODO: write useful common functions here, such as "select next".
	#Can maybe use self.parent.window.app.postEvent(…) here, like in main.py?
	
	def injectKeystrokes(self, key, *, count=1, modifier=Qt.NoModifier):
		"""Inject n keystrokes into the app, to the focused widget."""
		for _ in range(count):
			QApplication.instance().postEvent(
				QApplication.instance().focusWidget(), #window._screens[window.currentScreen],
				QKeyEvent(QKeyEvent.KeyPress, key, modifier) )
			QApplication.instance().postEvent(
				QApplication.instance().focusWidget(),
				QKeyEvent(QKeyEvent.KeyRelease, key, modifier) )
		
		
	def selectWidget(self, direction):
		"""Select the nth widget in the direction specified.
		
			example: `myWidget.selectWidget(2)` selects the widget
				_after_ the next widget in the focus chain.
		"""
		#TODO DDR 2019-07-11: Does this actually skip over widgets appropriately if direction > 1 as specified?
		
		nextFn = 'previousInFocusChain' if direction < 0 else 'nextInFocusChain'
		
		widgetToFocus = getattr(self, nextFn)()
		while (
			not issubclass(type(widgetToFocus), FocusablePlugin) or
			not widgetToFocus.isVisible() or
			widgetToFocus.focusPolicy() == Qt.NoFocus or #Focus policy mask is not inclusive of "none" or "click". See http://doc.qt.io/qt-5/qt.html#FocusPolicy-enum. Can't just test for equality, since radio buttons are weird - the dominate radio button's focusPolicy is 10, the unselected button is 11 I think. The only time we actually *care* wrt the jog wheel is when the focus is set to none or mouse, though. Ideally, we'd check for wheel focus, but that doesn't default and it would be a real pain in the neck changing the focus of everything from the default of 'strong'.
			widgetToFocus.focusPolicy() == Qt.ClickFocus
		):
			widgetToFocus = getattr(widgetToFocus, nextFn)()
		if hasattr(widgetToFocus, 'beforeJogWheelFocus'): #Emit the event, used by scroll list in inline mode to select the right entry.
			widgetToFocus.beforeJogWheelFocus(int(copysign(1, direction)))
		widgetToFocus.setFocus(Qt.OtherFocusReason)
		
		
		# Can't do this for focus, backtab doesn't work reliably when looping
		# over, arrow keys don't work unless compiled for apparently?
		#self.injectKeystrokes(Qt.Key_Tab, count=abs(direction),
		#	modifier=Qt.NoModifier if direction > 0 else Qt.ShiftModifier )
		
		#Show the focus ring here, since this is the function used by the jog
		#wheel to navigate widgets. We don't yet know which widget will be
		#focused next, that will dealt with by a refocus callback on the app.
		self.window().focusRing.show()
		self.window().focusRing.focusOut(immediate=True)

	
	#This prevents, among many other things, mouse up from firing for stylesheets.
	#It needs to fire the super event of the class which inherits it, which is an unknown here.
	#def mouseReleaseEvent(self, event) -> None:
	#	#event.ignore() #This doesn't work. :|
	#	#print('mouse', event, event.isAccepted())
	#	#if hasattr(super(), 'mouseReleaseEvent'):
	#	super(type(self)).mouseReleaseEvent(self, event)
	
	
	
	#Units are only really used for decimal spin boxes, but they affect the logic of the spin boxes, and the spin box logic is sort of shared with everything.
	
	def availableUnits(self) -> [str]:
		if not hasattr(self, 'units'):
			return ['']
		
		units = self.units
		if units == 'standard': #We usually only want these four common prefixes.
			units = 'n,µ,,k'
		if units == 'seconds': #We usually only want these four common prefixes.
			units = 'ns,µs,ms,s'
		
		units = sorted(
			[s.strip() for s in units.split(',')], #Strip to accept space in definition.
			key=lambda unit: self.knownUnits.get(unit[:1]) ) #Use get, which returns None on miss, so it doesn't fail before our nice assert.
		
		for unit in units: #See above for list of known units.
			assert unit[:1] in self.knownUnits, f'{self.window().objectName()}.{self.objectName()}: Unit "{unit}" not found in {units}.'
			
		self.availableUnits = lambda _: units #Cache results. We should never have to change units.
		return units
		
	
	def unit(self) -> str:
		return self.suffix() if hasattr(self, 'units') else ''
	
	def realValue(self) -> float:
		#Get real value of input, taking into account units such as 'k' or 'µs'.
		return (
			self.value() * self.knownUnits[self.suffix()[:1]]
			if hasattr(self, 'units') else 
			self.value() 
		)
	
	
	#Install event filter here to detect touch events and set
	#self.editMode appropriately. If the jog wheel is being used
	#to select, set self.editMode to 'jogwheel' instead in selectWidget.
	
	def eventFilter(self, obj, event):
		"""Event filter that provides touch signal events.
			
			Please override eventFilter2 in sub-classes."""
		
		if event.type() == QEvent.KeyPress:
			#This esc-key test is never even hit, I think it's caught by the global filter first.
			if event.key() == Qt.Key_Escape:
				event.ignore()
				return True
		
		if event.type() == QEvent.TouchBegin:
			self.touchStart.emit()
			return False #Don't swallow this event. You can filter it later in eventFilter2 and do so if needed.
		
		#This never fires. 🤷
		if event.type() == QEvent.TouchEnd:
			self.touchEnd.emit()
			return False
		
		#Work around the previous event not working. Brings up keyboard with mouse input, which normally shouldn't happen - the assumption is that if mouse is plugged in, a keyboard and mouse are plugged in, so the on-screen keyboard should not pop up.
		if event.type() == QEvent.MouseButtonRelease:
			self.touchEnd.emit()
			return False
		
		return bool(self.eventFilter2(obj, event))
	
	#Note: eventFilter seems to need to be a function in the class installing it on itself.
	def eventFilter2(self, obj, event):
		"""Override this instead of eventFilter."""
		pass