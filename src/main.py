# -*- coding: future_fstrings -*-

"""
Launch point for the Python QT back-of-camera interface.

See readme.md for more details.
"""

# General imports
import sys, time
from debugger import *; dbg

# QT-specific imports
from PyQt5 import QtWidgets, QtCore, QtGui
from stats import report

import settings
from hardware import Hardware
from widgets.focus_ring import FocusRing

#Our settings
PRECACHE_ALL_SCREENS = False

#Script setup
perf_start_time = time.perf_counter()

sys.path.append('src/widgets') #Add the components' path to import, because — since pyQt5 calculates the import path outside of our control — we can't import them from a subfolder like with the screens.
sys.path.append('src/lowpy')

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)



class Window(QtCore.QObject):
	"""Meta-controls (screen switching & keyboards) for the app.
	
			This class provides a high-level API to control the running
		application. Currently, that means controlling which screen is
		currently displayed and providing calls to enable an on-screen
		keyboard. It also provides some convenience for developing the
		application by restoring the last displayed screen.
		
		History:
			The current method of screen switching is pretty dumb, as it does
		not use the built-in QT switcher (QStackedLayout) and it relies on
		opening and closing qDialogs which aren't meant for long-term displays
		such as the main window. It is difficult to change, however, since it's
		hard-to- impossible to get the contents of a window (a QDialog in this
		case) in to a frame (a QWidget) which can be loaded into a
		QStackedLayout. The QDialogs just pop up as their own window when in
		the QStackedWidget.
		
			Maybe try something with setAttribute Qt::WA_DontShowOnScreen True
		or False? Perhaps that would remove the flicker that currently occurs
		during screen switches. I think that currently there's no flicker in
		the C++ app because the screen below is never closed. However, this
		won't work any more in a sane manner because of the introduction of
		more transparency to the UI.
		
			As to why each screen is a QDialog? All our dialogs were ported
		forward from before I got here, so it's just historic cruft at this
		point. I can't figure out what would be better to port them to anyway,
		since we can't seem to use a QMainWindow with a QStackedLayout unless
		we combine everything into one .ui file.
	"""
	
	def __init__(self, app):
		super().__init__()
		
		self.app = app
		app.window = self #Yuck. Couldn't find a decent way to plumb self.showInput through to the widgets otherwise.
		
		
		
		################################
		# Screen-loading functionality #
		################################
		
		from screens.about_camera import AboutCamera
		from screens.file_settings import FileSettings
		from screens.main import Main
		from screens.play_and_save import PlayAndSave
		from screens.power import Power
		from screens.primary_settings import PrimarySettings
		from screens.record_mode import RecordMode
		from screens.recording_settings import RecordingSettings
		from screens.stamp import Stamp
		from screens.trigger_delay import TriggerDelay
		from screens.triggers import Triggers
		from screens.update_firmware import UpdateFirmware
		from screens.user_settings import UserSettings
		from screens.test import Test
		from screens.service_screen import ServiceScreenLocked, ServiceScreenUnlocked
		from screens.remote_access import RemoteAccess
		from screens.storage import Storage
		
		self._availableScreens = {
			'main': Main, #load order, load items on main screen first, main screen submenus next, and it doesn't really matter after that. All screens get loaded in less than 10 seconds, so this is only a startup concern.
			'primary_settings': PrimarySettings,
			'recording_settings': RecordingSettings,
			'triggers': Triggers,
			'trigger_delay': TriggerDelay,
			'record_mode': RecordMode,
			'play_and_save': PlayAndSave,
			'about_camera': AboutCamera,
			'file_settings': FileSettings,
			'power': Power,
			'stamp': Stamp,
			'update_firmware': UpdateFirmware,
			'user_settings': UserSettings,
			'test': Test,
			'service_screen.locked': ServiceScreenLocked,
			'service_screen.unlocked': ServiceScreenUnlocked,
			'remote_access': RemoteAccess,
			'storage': Storage,
		}
		
		self._screens = {}
		
		# Set the initial screen. If in dev mode, due to the frequent restarts,
		# reopen the previous screen. If in the hands of an end-user, always
		# open the main screen when rebooting to provide an escape route for a
		# confusing or broken screen.
		
		#settings.setValue('current screen', 'widget_test')
		
		if settings.value('development mode', True):
			self.currentScreen = settings.value('current screen', 'main')
		else:
			self.currentScreen = 'main'
		
		if self.currentScreen not in self._availableScreens: 
			self.currentScreen = 'main'
		
		self._screenStack = ['main', self.currentScreen] if self.currentScreen != 'main' else ['main'] #Start off with main loaded into history, since we don't always start on main during development and going back should get you *somewhere* useful rather than crashing.
		
		self._ensureInstantiated(self.currentScreen)
		
		if hasattr(self._screens[self.currentScreen], 'onShow'):
			self._screens[self.currentScreen].onShow()
		self._screens[self.currentScreen].show()
		
		settings.setValue('current screen', self.currentScreen)
		
		#Cache all screens, cached screens load about 150-200ms faster I think.
		self._lazyLoadTimer = QtCore.QTimer()
		self._lazyLoadTimer.timeout.connect(self._loadAScreen)
		PRECACHE_ALL_SCREENS and self._lazyLoadTimer.start(250) #ms
		
		
		from input_panels.keyboard_numeric import KeyboardNumericWithUnits, KeyboardNumericWithoutUnits
		from input_panels.keyboard_alphanumeric import KeyboardAlphanumeric
		self._keyboards = {
			"numeric_with_units": KeyboardNumericWithUnits(self),
			"numeric_without_units": KeyboardNumericWithoutUnits(self),
			"alphanumeric": KeyboardAlphanumeric(self),
		}
		
		self._activeKeyboard = ''
		
	def _ensureInstantiated(self, screenName: str):
		"""Lazily load screens to shorten initial startup time."""
		
		if screenName in self._screens:
			return
		
		if screenName not in self._availableScreens:
			raise ValueError(f"Unknown screen {screenName}.\nAvailable screens are: {self._availableScreens.keys()}")
		
		screen = self._screens[screenName] = self._availableScreens[screenName](self)
		screen.app = self.app
		
		# So, we want alpha blending, so we can have a drop-shadow for our
		# keyboard. Great. Since we're not using a compositing window manager,
		# we don't get that between windows. So we don't want put the keyboard
		# in it's own window. (We could hack something together where the
		# shadow is in one window, and the keyboard in the other. This seems
		# rather confusing to me.) So, what we're going to do is to move all
		# the children of the loaded screen into a widget the size of the
		# screen, and the keyboard into another. This gives us -conceptually-
		# the same setup as in the old camApp, where keyboards were in a
		# separate container.
		
		children = screen.children()
		screenContents = QtWidgets.QWidget(screen)
		for child in children:
			child.setParent(screenContents)
		screen.screenContents = screenContents
		
		# Finally, add the screen's focus ring.
		screen.focusRing = FocusRing(self._screens[screenName])
		
	def _uninstantiatedScreens(self):
		"""Return (generator for) non-cached screens. (Those not in self._screens.)"""
		return (screen for screen in self._availableScreens.keys() if screen not in self._screens.keys())
		
	def _loadAScreen(self):
		screen = next(self._uninstantiatedScreens(), None)
		if not screen:
			self._lazyLoadTimer.stop()
			self._lazyLoadTimer.deleteLater()
			report("screen_cache_time", {"seconds": time.perf_counter() - perf_start_time})
		else:
			self._ensureInstantiated(screen)
	
	def show(self, screen):
		"""Switch between the screens of the back-of-camera interface.
		
		Example: self.uiPlayAndSave.clicked.connect(lambda: window.show('play_and_save'))"""
		
		# Prevent screen from disappearing entirely. Because we open the screen next screen then hide the current, if both are the same it shows then hides the screen so it goes away.
		if(screen == self.currentScreen):
			print(f'Warning: Tried to open {screen}, but it was already open. This probably indicates an application logic error.') # Also print a warning, because this probably indicates a logic error.
			return dbg() #This gets stubbed out in production, so it doesn't actually freeze the app.
		
		#If you loop through to a screen again, which can easily happen because we don't always use window.back() to return from screens, discard the loop to keep history from growing forever.
		self._screenStack += [screen]
		self._screenStack = self._screenStack[:self._screenStack.index(screen)+1]
		
		self._ensureInstantiated(screen)
		
		if hasattr(self._screens[screen], 'onShow'):
			self._screens[screen].onShow()	
		self._screens[screen].show()
		
		self._screens[self.currentScreen].hide()
		if hasattr(self._screens[self.currentScreen], 'onHide'):
			self._screens[self.currentScreen].onHide()
		# TODO: DDR 2018-06-11 Also hide the keyboard and anything else that needs cleanup.
		
		#Only set the setting value after everything has worked, to avoid trying to load a crashing screen.
		self.currentScreen = screen
		settings.setValue('current screen', screen)
		
		#print(f'current breadcrumb: {self._screenStack}')
		
	def back(self):
		"""Return to a previous screen."""
		if(len(self._screenStack) >= 2):
			self.show(self._screenStack[-2])
		else:
			print('Error: No more back to navigate to.')
	
	
	
	#############################
	# Input panel functionality #
	#############################
	
	def showInput(self, name: str, *, hints: list = [], focus: bool):
		"""Display a soft keyboard on-screen.
			
			name: Identifier string in self._keyboards.
			hints: Keyword, takes ['list', 'of', 'words'] to show as
				soft buttons at the top of the keyboard. Only
				applies to the alphanumeric keyboard.
			focus: Determines if the keyboard takes focus or not.
				Behaves like a modal dialog if it does focus."""
		
		if self.activeInputName() == name:
			return
		
		if self.activeInput():
			self.hideInput()
		
		self._activeKeyboard = name
		panel = self._keyboards[self._activeKeyboard]
		panel.setParent(self._screens[self.currentScreen])
		panel.onShow.emit({
			"opener": app.focusWidget(),
			"hints": hints,
			"focus": focus,
		})

	
	def hideInput(self):
		"""Hide the keyboard given by name, or the most recent keyboard."""
		
		if not self._activeKeyboard:
			return #Well, that was easy. *causes horrendous problems down the road*
		
		panel = self._keyboards[self._activeKeyboard]
		panel.onHide.emit()
		self._activeKeyboard = ''
	
	
	def activeInput(self):
		if self._activeKeyboard and self._keyboards[self._activeKeyboard].isVisible():
			return self._keyboards[self._activeKeyboard]
		else:
			return None
		
	
	def activeInputName(self):
		if self._activeKeyboard and self._keyboards[self._activeKeyboard].isVisible():
			return self._activeKeyboard
		else:
			return None
			


class GlobalFilter(QtCore.QObject):
	e = QtCore.QEvent #documented at https://doc.qt.io/qt-5/qevent.html
	knownEvents = frozenset([
		#Frequently-fired events and startup events. Ignored because way too many of them are fired.
		e.Close, e.Paint, e.UpdateRequest, e.MetaCall, e.PolishRequest, e.LayoutRequest, e.UpdateLater, e.Timer, e.ApplicationStateChange, e.ApplicationActivate, e.ApplicationDeactivate, 20, e.FocusIn, e.WindowActivate, e.ActivationChange, e.Expose, e.DeferredDelete, e.PaletteChange, e.FontChange, e.StyleChange, 15, e.WindowTitleChange, e.ChildAdded, e.ParentChange, e.CursorChange, e.MouseButtonDblClick, e.MouseButtonPress, e.MouseButtonRelease, e.MouseMove, e.MouseTrackingChange, e.Move, 152, e.HideToParent, e.Hide, e.ContentsRectChange, e.Polish, e.ChildPolished, e.DynamicPropertyChange, e.ChildRemoved, e.ZOrderChange, 16, e.ShowToParent, e.ApplicationPaletteChange, e.ThreadChange, e.ToolTip, e.ToolTipChange,
		
		#Input events, usually not important, we are after the effects.
		e.TouchBegin, e.TouchCancel, e.TouchEnd, e.TouchUpdate,
		e.SockAct, e.Leave, e.Enter, #SockAct is triggered by mouse movement.
		e.FocusAboutToChange, e.FocusIn, e.FocusOut,
		e.KeyPress, e.KeyRelease, e.ShortcutOverride, e.InputMethodQuery,
		e.ScrollPrepare, e.Scroll, e.Gesture, e.GestureOverride, #Related to PyQt5.QWidgets.QScroller.
		
		#Screen transition events
		e.PlatformSurface, e.WinIdChange, e.WindowIconChange, e.WindowDeactivate, e.WindowActivate, e.Resize, e.Show,
	])
	
	
	def __init__(self, app, window):
		super().__init__()
		
		self.app = app
		self.window = window
		
		self.touchStartTarget = None
	
	def eventFilter(self, obj, event):
		"""Global keyboard shortcuts and shortcut interception.
		
			This function eats up about half a second total startup
			time, about 1/10th of a second of immediate startup. It
			is called extremely often.
		"""
		
		events = QtCore.QEvent
		keys = QtCore.Qt
		
		#Stop escape from closing the camapp, if a keyboard is plugged in. Just exit the current screen, assuming widgets behave correctly.
		if event.type() == events.KeyPress:
			if event.key() == keys.Key_Escape:
				window.back()
				return True
			return False
		
		#Take note of the (focussable) target we touched. If we're still over it in the release event, then we accept it as having activated.
		if event.type() == events.TouchBegin:
			if hasattr(obj, 'isFocussable'):
				self.touchStartTarget = obj
			return False
			
		if event.type() == events.TouchEnd:
			#This only ever gets called with QWindows, so use the starter object and test geometry.
			#dbg()
			return False
		
		if event.type() in self.knownEvents:
			return False
		
		print('filtered', self, obj, event, event.type())
		return False
	


def connectHardwareEvents(app, hardware):
	def linkLightToRecordButton():
		hardware.recordingLightsAreLit = hardware.recordButtonPressed #This is dumb. Lambdas can call functions, this is a setter function, but I can't call it because it uses =. -_-
	
	#We don't have recording yet as a concept, so just link the record button to the recording lights. :p
	#This should become a d-bus call at some point.
	hardware.subscribe('recordButtonDown', linkLightToRecordButton)
	hardware.subscribe('recordButtonUp', linkLightToRecordButton)
	
	def injectSelect():
		app.postEvent(
			app.focusWidget() and app.focusWidget(), #window._screens[window.currentScreen],
			QtGui.QKeyEvent(
				QtGui.QKeyEvent.KeyPress if hardware.jogWheelPressed else QtGui.QKeyEvent.KeyRelease,
				QtCore.Qt.Key_Select,
				QtCore.Qt.NoModifier ) )
	
	
	#Jog wheel has some composite input events; in addition to down and up and rotate, there's also click (which is cancelled by a rotation or long-press) and long-press (which is cancelled by rotation or click).
	jogWheelLongClickTimer = QtCore.QTimer()
	jogWheelLongClickTimer.setTimerType(QtCore.Qt.PreciseTimer)
	jogWheelLongClickTimer.setInterval(750)
	jogWheelLongClickTimer.timeout.connect(lambda: app.focusWidget().jogWheelLongPress.emit())
	jogWheelLongClickTimer.setSingleShot(True)
	
	pressTarget = None
	
	def startPress():
		nonlocal pressTarget
		jogWheelLongClickTimer.start()
		pressTarget = app.focusWidget()
	
	def endPress():
		nonlocal pressTarget
		
		if jogWheelLongClickTimer.isActive(): #Long-press timer hasn't expired, just a click.
			pressTarget = None
			app.focusWidget() and app.focusWidget().jogWheelClick.emit()
			jogWheelLongClickTimer.stop() #Suppress jog wheel long press.
	
	def cancelPress(_):
		nonlocal pressTarget
		
		#Cancel a click or long-press when the wheel is rotated.
		if app.focusWidget() and app.focusWidget().jogWheelRotationCancelsClick:
			pressTarget = None
			app.focusWidget() and app.focusWidget().jogWheelCancel.emit()
			if jogWheelLongClickTimer.isActive():
				jogWheelLongClickTimer.stop()
	
	hardware.subscribe('jogWheelDown', startPress)
	hardware.subscribe('jogWheelDown', lambda: app.focusWidget().jogWheelDown.emit())
	hardware.subscribe('jogWheelUp', lambda: app.focusWidget().jogWheelUp.emit())
	hardware.subscribe('jogWheelUp', endPress) #Must be after jogWheelUp event.
	hardware.subscribe('jogWheelHighResolutionRotation', lambda direction:
		app.focusWidget() and app.focusWidget().jogWheelHighResolutionRotation.emit(direction, hardware.jogWheelPressed) )
	hardware.subscribe('jogWheelLowResolutionRotation', cancelPress ) #High resolution rotation to cancel a click or long press is too finicky.
	hardware.subscribe('jogWheelLowResolutionRotation', lambda direction:
		app.focusWidget() and app.focusWidget().jogWheelLowResolutionRotation.emit(direction, hardware.jogWheelPressed) )
	
	def focusChanged(old, new):
		nonlocal pressTarget
		
		pressTarget and pressTarget.jogWheelCancel.emit()
		pressTarget = None
		jogWheelLongClickTimer.stop()
		
	app.focusChanged.connect(focusChanged)



if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	app.setFont(QtGui.QFont("DejaVu Sans", 12)) #Fix fonts being just a little smaller by default than in Creator. This probably only applies to the old camApp .ui files.
	
	window = Window(app)
	
	eventFilter = GlobalFilter(app, window)
	app.installEventFilter(eventFilter)
	app.setStyleSheet("""
		/* Remove the little dotted focus ring. It's too hard to see, but still looks messy now that we've got our own. */
		*:focus {
			outline: 2px double blue; /*Debugging, show system focus ring.*/
			outline: none;
			outline-offset: 5px; /* This doesn't work. 😑 */
			/*outline-radius: 5px;*/
		}
	""")
	
	def focusChanged(old, new):
		if new:
			window._screens[window.currentScreen].focusRing.focusOn(new)
			window._screens[window.currentScreen].focusRing.focusOut(immediate=True)
		else:
			#hide on screen transition
			window._screens[window.currentScreen].focusRing.hide()
	app.focusChanged.connect(focusChanged)

	
	forceHardwareInstantiation = False #This should be an env var.
	if forceHardwareInstantiation:
		hardware = Hardware()
		connectHardwareEvents(app, hardware)
	else:
		try:
			hardware = Hardware() #Must be instantiated like this, I think the event pump timer gets eaten by GC otherwise.
			connectHardwareEvents(app, hardware)
		except Exception as e:
			#We're probably in the VM, just print a message.
			print('Could not initialize camera hardware.')
	
	
	report("start_up_time", {"seconds": time.perf_counter() - perf_start_time})
	
	sys.exit(app.exec_())