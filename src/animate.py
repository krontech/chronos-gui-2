# -*- coding: future_fstrings -*-

"""Set up toggle menu.
	
	- Animates open/closed, and can reverse track mid-animation.
	- Handles jog wheel focus appropriately.
	- Hides when in "closed" position.
	- Convenient and Easy-To-Use™ API.
	
	Basically, after reading https://doc.qt.io/qt-5/animation-overview.html, and
	then https://doc.qt.io/qt-5/statemachine-api.html which was used to handle
	animation logic, I proceeded to read https://q3k.org/birdfeeder.pdf which
	quite frankly was a lot easier to digest."""

from typing import Union, List, Tuple, Callable
from random import randint

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QPropertyAnimation, QPoint, QTimer

from debugger import *; dbg


class MenuToggle():
	"""An object for motion-based menu toggling.
		
		Constructor Args:
			menu: The menu to be toggled.
			button: A widget, or list of widgets, which have a
				clicked signal.
			xRange: A tuple containing a start position and end
				position for the menu to animate between. The
				menu will be hidden when in the start position.
				The y coordinate is set visually, by moving the
				menu in the .ui files.
			invisiblePadding = 0: Compensate for touch margins. Touch
				margins are assumed to stick out in the direction
				of the opening motion.
			duration = 17: Of the animation, in ms."""
	
	def __init__(
		self, *, 
		menu: QWidget,
		button: Union[QWidget, List[QWidget]],
		focusTarget: QWidget = None, #Set to a widget to have the widget focused when the panel opens. Menu is focussused otherwise.
		xRange: Tuple[int, int],
		invisiblePadding: int = 0, 
		duration: int = 17 #ms
	):
		"""An object represeting opening and closing a menu.
			
			When created, instantiates a bunch of behaviour to make
				menus open and close correctly with regards to fast
				taps and the jog wheel."""
		
		super().__init__()
		
		self._menu = menu
		menu.menu_action = self #Preserve reference, 'cause GC plays bad otherwise.
		menu.hide() #All menus start closed.
		
		self._buttons = button if button is list else [button]
		
		self._focusTarget = focusTarget
		
		#Can't extract invisiblePadding from the CSS without string parsing.
		if xRange[0] < xRange[1]:
			hiddenAt = QPoint(xRange[0] + invisiblePadding, menu.y())
		else:
			hiddenAt = QPoint(xRange[0] - invisiblePadding, menu.y())
		shownAt = QPoint(xRange[1], menu.y())
		
		self._anim = anim = QPropertyAnimation(menu, b"pos")
		setattr(menu, f'toggle{randint(0,99999999)}', anim) #keep minimal reference without explicitly parenting
		anim.setDuration(duration) #framerate ms (?) * frames to animate, excluding start and end frame?
		anim.setStartValue(hiddenAt)
		anim.setEndValue(shownAt)
		anim.finished.connect(self.__animationFinished)
		
		for button in self._buttons:
			button.clicked.connect(self.toggle)
		
		menu.focusOutEvent = self.checkHide
	
	
	def toggle(self):
		"""Start to show the menu, or start to hide the menu if it's already opened."""
		self._menu.show()
			
		if self._anim.currentTime() == 0 or self._anim.direction() == QPropertyAnimation.Backward:
			self._anim.setDirection(QPropertyAnimation.Forward)
			(self._focusTarget or self._menu).setFocus()
			for button in self._buttons:
				button.keepActiveLook = True
				button.refreshStyle()
		else:
			self._anim.setDirection(QPropertyAnimation.Backward)
			for button in self._buttons[:1]:
				button.setFocus() #Meh. Just select the first one, might be fine.
			
		if self._anim.state() == QPropertyAnimation.Stopped:
			self._anim.start()
	
	def checkHide(self, *_):
		"""Start to hide the menu, if not in use."""
		
		# The button to toggle this menu is now focused, and will
		# probably toggle it shut. Don't close the menu, or it would
		# toggle it open again.
		if any(button.hasFocus() for button in self._buttons):
			return
		
		# Don't close when a sub-element is selected. This has to be
		# taken care of manually by the sub-element, because in the
		# focus assist menu not all buttons go to other screens.
		return
		if any(child.hasFocus() for child in self._menu.children()):
			return
		
		self._anim.setDirection(QPropertyAnimation.Backward)
		
		if self._anim.state() == QPropertyAnimation.Stopped:
			self._anim.start()
		
		# The original idea was animate margin left and button width, instead
		# of the menu position, so that the buttons were always fully
		# clickable even before they'd appeared. However, as it seems
		# effectively impossible to change the margin of a button without
		# going through (text-based) CSS, we just animate the whole menu. :(
		
		#child = menu.children()[0]
		#margins = child.contentsMargins() #doesn't work, probably qt bug - just returns 0,0,0,0
		#margins = child.style().subElementRect(QtWidgets.QStyle.SE_PushButtonFocusRect, QtWidgets.QStyleOptionButton(), child) #doesn't work, returns … default margins? I'm not sure what 21,21,-22,-22 is.
		#margins = ???
	
	
	def forceHide(self, *_):
		"""Start to hide the menu, even if something's focussed on it."""
		self._anim.setDirection(QPropertyAnimation.Backward)
		if self._anim.state() == QPropertyAnimation.Stopped:
			self._anim.start()
	
	def show(self, *_):
		"""Start to show the menu. Inverse of checkHide or forceHide."""
		self._anim.setDirection(QPropertyAnimation.Forward)
		if self._anim.state() == QPropertyAnimation.Stopped:
			self._anim.start()
	
	
	def __animationFinished(self):
		"""Actually hide the menu when the menu hiding animation finishes."""
		if self._anim.direction() == QPropertyAnimation.Backward:
			self._menu.hide()
			for button in self._buttons:
				button.keepActiveLook = False
				button.refreshStyle()



def delay(parent, timeout: int, callback: Callable[[], None], paused: bool = False):
	"""Delay ms before calling timeout.
		
		Args:
			timeout: in ms, before calling callback
			callback: invoked after some timeout
			paused = False: don't start the timer upon creation
		
		Yield:
			The underlying QTimer object."""
	
	timer = QTimer()
	timerId = f'__delayTimer{hex(randint(0,99999999))}'
	setattr(parent, timerId, timer)  #keep minimal reference without explicitly parenting
	timer.timeout.connect(callback)
	timer.timeout.connect(lambda: delattr(parent, timerId))
	timer.setInterval(timeout) #ms
	timer.setSingleShot(True)
	paused or timer.start()
	return timer