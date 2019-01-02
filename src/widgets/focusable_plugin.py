from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent

from debugger import *; dbg

class FocusablePlugin():
	"""Some behaviour to make focusable widgets work correctly.
	
		Touch and jog wheel have subtly different requirements. Jog wheel can
		focus in to a widget and then have sub-focusses, for example. Keyboard
		(software input) has additional data requirements such as units and
		desired input type.
	"""
	
	#Subscribe to these signals in the parent class.
	jogWheelRotationCancelsClick = True
	jogWheelDown = pyqtSignal()
	jogWheelUp = pyqtSignal() #fired before click
	jogWheelLowResolutionRotation = pyqtSignal(int, bool) #direction, -1 or +1; jog wheel is depressed
	jogWheelHighResolutionRotation = pyqtSignal(int, bool) #direction, -1 or +1; jog wheel is depressed
	jogWheelClick = pyqtSignal() #a tap on the jog wheel, cancelled by rotation or long press
	jogWheelLongPress = pyqtSignal() #long press of jog wheel, cancelled by rotation or click
	jogWheelCancel = pyqtSignal() #click/long-press is aborted by jog wheel rotation
	
	#Specify the widget property "units", on numeric inputs, to provide a list of units to choose from. It is recommended to stick to 4, since that's how many unit buttons are on the numeric keyboard. Units can be scrolled with the jog wheel.
	unitList = ['y', 'z', 'a', 'f', 'p', 'n', 'µ', 'm', '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
	knownUnits = { #Map of units to their multipliers. eg, k = kilo = ×1000. Or µs = microseconds = ×0.000001. Usually queried with unit[:1], because something like mV or ms both have the same common numerical multiplier. [0] is not used because it fails on "".
		suffix: 10**(index-8)*3 for index, suffix in enumerate(unitList) #Position 8 is neutral, 'no unit'.
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
				widgetToFocus.focusPolicy() == Qt.NoFocus or 
				widgetToFocus.focusPolicy() == Qt.ClickFocus ): #Focus policy mask is not inclusive of "none" or "click". See http://doc.qt.io/qt-5/qt.html#FocusPolicy-enum. Can't just test for equality, since radio buttons are weird - the dominate radio button's focusPolicy is 10, the unselected button is 11 I think. The only time we actually *care* wrt the jog wheel is when the focus is set to none or mouse, though. Ideally, we'd check for wheel focus, but that doesn't default and it would be a real pain in the neck changing the focus of everything from the default of 'strong'.
			widgetToFocus = getattr(widgetToFocus, nextFn)()
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
		
		
	
	def changeJogWheelCharacterSelection(self, delta: int):
		"""Change the jog wheel highlight, relative to where it was last.
		
			Defaults to highlighting the second-largest magnitude place."""
			
		edit = self.lineEdit()
		val = self.text()[len(self.prefix()):-len(self.suffix()) or None] #or None: -0 is as 0, and trims from the first element of the index, yielding '' always. None behaves like str[n:], which is what we want.
		
		nextPos = self.jogWheelIndex - delta
		try:
			decimalPlace = val.index('.')
			if decimalPlace >= nextPos:
				strIndex = nextPos + 1 #account for decimal place
				decimals = True
			else:
				strIndex = nextPos
				decimals = False
		except ValueError:
			strIndex = nextPos
			decimals = False
			
		if nextPos < 0:
			nextPos = 0
			if len(val) and not self.value() > self.maximum():
				edit.setText(f'{self.prefix()}0{val}{self.suffix()}')
		elif strIndex >= len(val):
			if(decimals and val[-1] != '0'): #allow selecting additional zeros, probably plays badly with precision restrictions though
				nextPos = len(val) - decimals
				edit.setText(f'{self.prefix()}{val}0{self.suffix()}')
			else:
				nextPos = len(val) - decimals - 1
		
		self.jogWheelIndex = nextPos
		edit.setSelection(len(self.prefix())+nextPos+decimals, 1)
		
	
	def highlightNumberOrdinal(self, position):
		"""Highlight the character at position, counting digits from left."""
			
		val = self.text()[len(self.prefix()):-len(self.suffix()) or None] #or None: -0 is as 0, and trims from the first element of the index, yielding '' always. None behaves like str[n:], which is what we want.
		
		try:
			decimalPlace = val.index('.')
			if decimalPlace >= position:
				decimals = True
			else:
				decimals = False
		except ValueError:
			decimals = False
		
		self.lineEdit().setSelection(len(self.prefix()) + position + decimals, 1)
	
	
	def incrementJogWheelCharacterSelection(self, place: int, delta: int, keepOrderOfMagnitude: bool=True):
		"""Increment the jog wheel character selection by delta.
			
			Args:
				place: 0-indexed offset from the left side of the number.
				delta: ±n to add to the current value at place. Iterative, so keep small please!
				keepOrderOfMagnitude: Boolean, set to False to stop jogWheelIndex from tracking to an order of magnitude instead of left-based index, when the number of digits changes.
			
			If desired, jog wheel chaacter selection may be
			overridden by specifying place=n."""
			
		#Jog Wheel Incrementing:
		#- Sanity checking, since we need to iterate to add delta correctly across magnitude boundaries.
		#	- Clamp digit active to available digits.
		#- Increment/decrement digits.
		#- SingleStep needs to be accounted for (eg, ±16 vs ±1)
		#- Adjust focus digit if number of digits has changed. If in "1% mode"
		#- Validation limits. (min/max, % single step)
		#- Leading and trailing zeros. Decimal point.
		#- Special Case: Moving MSD past 0 should decrement (and select) 2nd MSD.
		#- Special Case: Increment/decrement pre/postfixes
		
		if delta > 20:
			print(f'Performance warning: incrementJogWheelCharacterSelection passed large delta ({delta}) to iterate.')
		
		Δsign = 1 if delta > 0 else -1
		
		val = self.text()[len(self.prefix()):-len(self.suffix()) or None] #or None: -0 is as 0, and trims from the first element of the index, yielding '' always. None behaves like str[n:], which is what we want.
		
		place = min(place, len(val)-1)
		
		for _ in range(abs(delta)):
			try:
				pointIndex = val.index('.')
				num = float(val)
			except ValueError:
				pointIndex = len(val)
				num = int(val or '0')
			
			magnitude = (pointIndex - place) + (place >= pointIndex)
			
			#First round, calculate magnitude max.
			nextValueA = round(num + Δsign*10**(magnitude-1), 16)
			lengthDeltaA = len(str(nextValueA)) - len(val)
			
			if(lengthDeltaA > 0):
				lengthDeltaA = 0
			
			#Second round, use first round length to calculate magnitude min.
			#Even if the first length delta is nonzero, the second may be zero.
			nextValueB = round(num + Δsign*10**(magnitude-1+lengthDeltaA), 16)
			lengthDeltaB = len(str(nextValueB)) - len(val)
			
			if keepOrderOfMagnitude:
				val = str(nextValueA) #Prepare for next iteration.
				self.jogWheelIndex += lengthDeltaB #Move order of magnitude. Seems wrong, doesn't it?
			else:
				val = str(nextValueB) #Prepare for next iteration.
			
		
		#Validation
		strPlace = place + (keepOrderOfMagnitude and (lengthDeltaA or lengthDeltaB)) + ((place + (keepOrderOfMagnitude and (lengthDeltaA or lengthDeltaB))) >= pointIndex)
		print(val, self.validate(val, strPlace))
		breakIf(self)
		self.lineEdit().setText(val)
		
		print('adjust', keepOrderOfMagnitude and (lengthDeltaA or lengthDeltaB), 'from', place)
		
		#adjust selection if nonfractional number digits changed, since we're left-indexed
		self.highlightNumberOrdinal(place + (keepOrderOfMagnitude and (lengthDeltaA or lengthDeltaB))) #effectively, just recompute the highlight
	
	
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
			key=lambda unit: knownUnits.get(unit[:1]) ) #Use get, which returns None on miss, so it doesn't fail before our nice assert.
		
		for unit in units: #See above for list of known units.
			assert unit[:1] in knownUnits, f'{self.window().objectName()}.{self.objectName()}: Unit "{unit}" not found in {units}.'
			
		self.availableUnits = lambda _: units #Cache results. We should never have to change units.
		return units
		
	
	def unit(self) -> str:
		return self.suffix() if hasattr(self, 'units') else ''
	
	def realValue(self) -> float:
		#Get real value of input, taking into account units such as 'k' or 'µs'.
		return (
			self.value() * knownUnits[self.suffix()[:1]]
			if hasattr(self, 'units') else 
			self.value() 
		)
	
	
	#Install event filter here to detect touch events and set
	#self.editMode appropriately. If the jog wheel is being used
	#to select, set self.editMode to 'jogwheel' instead in selectWidget.