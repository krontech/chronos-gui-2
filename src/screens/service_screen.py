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
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		self.window_ = window
		
		self.uiPassword.setText('') #Clear placeholder text.
		self.uiPassword.textChanged.connect(lambda text:
			text == "4242" and window.show('service_screen.unlocked') )
		
		self.uiDone.clicked.connect(window.back)
	
	
	def onShow(self):
		api.get('cameraSerial').then(lambda serial:
			serial or self.window_.show('service_screen.unlocked'))



class ServiceScreenUnlocked(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/service_screen.unlocked.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
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