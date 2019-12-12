# -*- coding: future_fstrings -*-
import os
from datetime import datetime
import logging; log = logging.getLogger('Chronos.gui')

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

import chronosGui2.api as api
import chronosGui2.settings as settings

from chronosGui2.generated.chronos import Ui_ServiceScreenLocked
from chronosGui2.generated.chronos import Ui_ServiceScreenUnlocked

class ServiceScreenLocked(QtWidgets.QDialog, Ui_ServiceScreenLocked):
	unlockPassword = "4242"
	
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		self.window_ = window
		
		self.uiPassword.setText('') #Clear placeholder text.
		self.uiPassword.textChanged.connect(self.checkPassword)
		
		self.uiDone.clicked.connect(window.back)
	
	
	def onShow(self):
		api.get('cameraSerial').then(self.onShow2)
	def onShow2(self, serial):
		#The camera has a serial number set before leaving the factory. If the
		#camera doesn't have a serial number, then it must still be in the
		#production process and we should unlock the service screen for the
		#technologist working on it.
		if not serial:
			self.unlock()
		
		#Check the password, if it's already been set then just go on through.
		#This resets when the camera is rebooted.
		self.checkPassword(self.uiPassword.text())
	
	def checkPassword(self, guess):
		if guess == self.unlockPassword:
			self.unlock()
	
	def unlock(self):
		self.window_.show('service_screen.unlocked')
		
		



class ServiceScreenUnlocked(QtWidgets.QDialog, Ui_ServiceScreenUnlocked):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
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
		
		self.uiDone.clicked.connect(lambda: window.show('main'))
	
	
	
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
