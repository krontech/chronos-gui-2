from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
# import api_mock as api


class ServiceScreenLocked(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi("src/screens/service_screen.locked.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		self.showEvent = self.delayedUnlock
		self.windowControl = window
		
		self._delayedUnlockTimer = QtCore.QTimer()
		self._delayedUnlockTimer.setSingleShot(True)
		self._delayedUnlockTimer.timeout.connect(self.unlock)
		
		# Button binding.
		self.uiPassword.textChanged.connect(self.unlock)
			
		self.uiDone.clicked.connect(window.back)

	def unlock(self, *_):
		if self.uiPassword.text() == "4242":
			self.windowControl.show('service_screen.unlocked')
	
	def delayedUnlock(self, *_):
		"""Hack around self.show during self.showEvent not behaving."""
		self._delayedUnlockTimer.start(0) #ms

class ServiceScreenUnlocked(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi("src/screens/service_screen.unlocked.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(lambda: window.show('primary_settings'))