# -*- coding: future_fstrings -*-
from datetime import datetime
import logging; log = logging.getLogger('Chronos.gui')

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg

import api2 as api
import settings


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
		self.uiPassword.setText('')
		self.uiPassword.textChanged.connect(self.unlock)
			
		self.uiDone.clicked.connect(window.back)

	def unlock(self, *_):
		if self.uiPassword.text() == "4242" or settings.value('skip factory authentication', True):
			settings.setValue('skip factory authentication', False) #First entry is free. Saves one password for production when they set serial and run cal.
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
		self.uiCalibratedOnTemplate = self.uiCalibratedOn.text()
		
		# Button binding.
		api.observe('cameraSerial', self.recieveSerial)
		self.uiSerialNumber.textChanged.connect(self.sendSerial)
	
		self.uiCal.clicked.connect(self.runCal)
		
		settings.observe('last factory cal', None, self.recieveFactoryCalDate)
		
		settings.observe('debug controls enabled', False, lambda x:
			self.uiShowDebugControls.setChecked(x) )
		self.uiShowDebugControls.stateChanged.connect(lambda x:
			settings.setValue('debug controls enabled', bool(x)) )
		
		self.uiDone.clicked.connect(lambda: window.show('primary_settings'))
	
	
	
	@pyqtSlot(int)
	def recieveSerial(self, value):
		self.uiSerialNumber.setText(value)
	
	def sendSerial(self, value):
		log.error("There is a command to set this, but it only works on Arago.")
	
	def runCal(self):
		settings.setValue('last factory cal', 
			datetime.now().strftime(self.uiCalibratedOnTemplate))
		log.error("We don't have these routines in the API yet.")
	
	def recieveFactoryCalDate(self, msg):
		if not msg:
			self.uiCalibratedOn.hide()
		else:
			self.uiCalibratedOn.setText(msg)