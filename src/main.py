"""
Launch point for the Python QT back-of-camera interface.

Usage:
	With the camera dbus api running, run python3 cam-ui.py. Python 3.6 is
required. The dbus api, and dbus api mock, is available from the chronos-cli
repository.

See readme.md for more details.
"""

# General imports
import sys
import pdb
from debugger import dbg, brk; dbg, brk

# QT-specific imports
from PyQt5 import QtWidgets, QtCore


sys.excepthook = lambda t, v, tb: (
	QtCore.pyqtRemoveInputHook(),
	pdb.traceback.print_exception(t, v, tb),
	pdb.post_mortem(t=tb)
)

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

settings = QtCore.QSettings('Krontech', 'back-of-camera interface')



class Window():
	"""Metacontrols (screen switching) for the back of camera interface.
	
	This class provides a high-level API to control the running application.
	Currently, that means controlling which screen is currently displayed. It
	also provides some convenience for developing the application by restoring
	the last displayed screen.
	
	History:
		The current method of screen switching is pretty dumb, as it does
	not use the built-in QT switcher (QStackedLayout) and it relies on
	opening and closing qDialogs which aren't meant for long-term displays
	such as the main window. It is difficult to change, however, since it's
	hard-to- impossible to get the contents of a window (a QDialog in this
	case) in to a frame (a QWidget) which can be loaded into a
	QStackedLayout. The QDialogs just pop up as their own window when in
	the QStackedWidget.
	As to why each screen is a QDialog? All our dialogs were ported forward
	from before I got here, so it's just historic cruft at this point. I
	can't figure out what would be better to port them to anyway, since we
	can't seem to use a QMainWindow with a QStackedLayout unless we combine
	everything into one .ui file.
	
	Methods:
		show(string id): Switch the currently open screen. Similar to
			QStackedLayout, but provides a string-indexed interface versus an
			int-indexed interface.
	"""
	
	def __init__(self):
		from screens.main import Main
		from screens.recording_settings import RecordingSettings
		from screens.recording_mode import RecordingMode
		from screens.trigger_delay import TriggerDelay
		from screens.trigger_settings import TriggerSettings
		from screens.settings import Settings
		
		self._screens = {
			'main': Main(self),
			'recording settings': RecordingSettings(self),
			'recording mode': RecordingMode(self),
			'trigger delay': TriggerDelay(self),
			'trigger settings': TriggerSettings(self),
			'settings': Settings(self),
		}
		
		# Set the initial screen. If in dev mode, due to the frequent restarts,
		# reopen the previous screen. If in the hands of an end-user, always
		# open the main screen when rebooting to provide an escape route for a
		# confusing or broken screen.
		if settings.value('development mode', True):
			self.currentScreen = settings.value('current screen', 'main')
		else:
			self.currentScreen = 'main'
		
		if self.currentScreen not in self._screens: 
			self.currentScreen = 'main'
		
		self._screens[self.currentScreen].show()
		settings.setValue('current screen', self.currentScreen)
	
	def show(self, screen):
		"""Switch between the screens of the back-of-camera interface."""
		
		self._screens[self.currentScreen].hide()
		# TODO: DDR 2018-06-11 Also hide the keyboard and anything else that needs cleanup.
		
		self.currentScreen = screen
		self._screens[screen].show()
		settings.setValue('current screen', screen) #Only set the setting value after, so we don't accidentally restore to a non-existent window.





app = QtWidgets.QApplication(sys.argv)

window = Window()

sys.exit(app.exec_())