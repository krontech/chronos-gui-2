# -*- coding: future_fstrings -*-
from datetime import datetime
import logging; log = logging.getLogger('Chronos.gui')
from smbus2 import SMBus

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QTimer

import chronosGui2.api as api
import chronosGui2.settings as settings
from chronosGui2.debugger import *; dbg

if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_ServiceScreenLocked
	from chronosGui2.generated.txpro import Ui_ServiceScreenUnlocked
else:
	from chronosGui2.generated.chronos import Ui_ServiceScreenLocked
	from chronosGui2.generated.chronos import Ui_ServiceScreenUnlocked

class ServiceScreenLocked(QtWidgets.QDialog, Ui_ServiceScreenLocked):
	unlockPassword = "4242"
	
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)

		# API init.
		self.control = api.control()

		# Shipping mode timer init
		self.shippingModeStatusTimer = QTimer()
		self.shippingModeStatusTimer.timeout.connect(self.shippingModeStatus)
		self.shippingModeStatusTimer.setInterval(1000)
		self.shippingModeStatusTimer.start()
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		self.window_ = window
		
		self.uiPassword.setText('') #Clear placeholder text.
		self.uiPassword.textChanged.connect(self.checkPassword)

		self.uiShippingMode.setChecked(self.control.getSync('shippingMode'))
		self.uiShippingMode.stateChanged.connect(self.setShippingMode)

		self.uiDone.clicked.connect(window.back)
	
	
	def onShow(self):
		self.control.get('cameraSerial').then(self.onShow2)
		
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

	def setShippingMode(self, value):
		self.control.setSync({'shippingMode' : bool(value)})
	
	def shippingModeStatus(self):
		if (self.control.getSync('shippingMode')):
			self.shippingModeMessage.showMessage('Shipping Mode Enabled\n\nOn the next restart, the AC adapter must be plugged in to turn the camera on.')
		else:
			self.shippingModeMessage.showMessage('Shipping Mode Disabled')

	def unlock(self):
		self.window_.show('service_screen.unlocked')
		
		



class ServiceScreenUnlocked(QtWidgets.QDialog, Ui_ServiceScreenUnlocked):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)

		# API init.
		self.control = api.control()

		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		self.uiCalibratedOnTemplate = self.uiCalibratedOn.text()
		
		# Button binding.
		api.observe('cameraSerial', self.recieveSerial)
		self.uiSetSerialBtn.clicked.connect(self.sendSerial)
	
		self.uiCal.clicked.connect(self.runCal)

		self.uiExportCalData.clicked.connect(self.runExportCalData)

		self.uiImportCalData.clicked.connect(self.runImportCalData)
		
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
		SERIAL_NUMBER_MAX_LEN = 16
		inputStr = self.uiSerialNumber.text()
		serialNum = inputStr[:SERIAL_NUMBER_MAX_LEN]

		try:
			with SMBus(1) as bus:
				# Set the write address MSB and LSB of the eeprom
				bus.write_byte(0x54, 0)
				bus.write_byte(0x54, 0)

				data = [ord(character) for character in serialNum] # Convert input to ascii byte
				data.insert(0,0) # The first byte written completes the LSB of the write address
				bus.write_i2c_block_data(0x54, 0, data)

		except Exception as e:
			log.error(str(e))
	
	def runCal(self):
		settings.setValue('last factory cal', 
			datetime.now().strftime(self.uiCalibratedOnTemplate))
		log.error("We don't have these routines in the API yet.")

	def recieveFactoryCalDate(self, msg):
		if not msg:
			self.uiCalibratedOn.hide()
		else:
			self.uiCalibratedOn.setText(msg)

	def runExportCalData(self):
		self.control.call('exportCalData', {})
		self.uiFactoryCalStatus.showMessage('Exporting calibration data, please wait.')


	def runImportCalData(self):
		self.control.call('importCalData', {})
		self.uiFactoryCalStatus.showMessage('Importing calibration data, please wait.')