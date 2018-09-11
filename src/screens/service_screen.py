from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


class ServiceScreenLocked(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
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
		uic.loadUi("src/screens/service_screen.unlocked.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		api.observe('cameraSerial', self.updateSerial)
		self.uiSerialNumber.textChanged.connect(lambda x: 
			api.set({'cameraSerial': x}))
		
		# Button binding.
		self.uiDone.clicked.connect(lambda: window.show('primary_settings'))
	
	
	@pyqtSlot(int)
	@silenceCallbacks('uiSerialNumber')
	def updateSerial(self, value):
		self.uiSerialNumber.setText(value)