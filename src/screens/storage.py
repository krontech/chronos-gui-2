# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore

from debugger import *; dbg

import api


class Storage(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/storage.ui", self)
		
		self.externalStorage = []
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self._usbFormatTimer = QtCore.QTimer()
		self._usbFormatTimer.setSingleShot(True)
		self._usbFormatTimer.timeout.connect(self.finishFormattingUSB)
		self._sdFormatTimer = QtCore.QTimer()
		self._sdFormatTimer.setSingleShot(True)
		self._sdFormatTimer.timeout.connect(self.finishFormattingSD)
		self._testNetworkStorageTimer = QtCore.QTimer()
		self._testNetworkStorageTimer.setSingleShot(True)
		self._testNetworkStorageTimer.timeout.connect(self.finishTestNetworkStorage)
		
		# Button binding.
		self.uiFormatUSB.clicked.connect(self.startFormattingUSB)
		self.uiEjectUSB.clicked.connect(self.ejectUSB)
		self.uiFormatSD.clicked.connect(self.startFormattingSD)
		self.uiEjectSD.clicked.connect(self.ejectSD)
		
		api.observe('externalStorage', self.updateMountedDeviceList)
		
		self.uiTestNetworkStorage.clicked.connect(self.testNetworkStorage)
		
		self.uiFileSaving.clicked.connect(lambda: window.show('file_settings'))
		self.uiDone.clicked.connect(window.back)
	
	
	def startFormattingUSB(self):
		self.uiFormatUSB.setEnabled(False)
		
		usbs = [s for s in self.externalStorage if s['interface'] == 'usb']
		if not usbs:
			self.uiUSBStorageFeedback.showError('No USB drive recognised.')
		elif len([s for s in usbs if s['device'] != usbs[0]['device']]) > 1:
			self.uiUSBStorageFeedback.showError('Multiple USB drives available.\nPlease disconnect all but one.')
		else:
			self.uiUSBStorageFeedback.showMessage(f'Formatting {usbs[0]["device"]}…\nPlease stand by.')
			self._usbFormatTimer.start(16*2) #Next frame, hopefully, so the above message displays. The format call can block for some time.
	
	def startFormattingSD(self):
		self.uiFormatSD.setEnabled(False)
		
		sds = [s for s in self.externalStorage if s['interface'] == 'sd']
		if not sds:
			self.uiSDStorageFeedback.showError('No SD drive recognised.')
		elif len([s for s in sds if s['device'] != sds[0]['device']]) > 1:
			self.uiSDStorageFeedback.showError('Multiple SD cards available.\nPlease remove all but one.')
		else:
			self.uiSDStorageFeedback.showMessage('Formatting SD card…\nPlease stand by.')
			self._sdFormatTimer.start(16*2) #Next frame, hopefully, so the above message displays. The format call can block for some time.
	
	
	def finishFormattingUSB(self):
		api.control('formatStorage', #This could take a while.
			[s for s in self.externalStorage if s['interface'] == 'usb'][0]['device'] )
		
		self.uiUSBStorageFeedback.showMessage('USB formatting complete.', timeout=None)
		self.uiFormatUSB.setEnabled(True)
	
	def finishFormattingSD(self):
		api.control('formatStorage', #This could take a while.
			[s for s in self.externalStorage if s['interface'] == 'sd'][0]['device'] )
		
		self.uiSDStorageFeedback.showMessage('SD card formatted.', timeout=None)
		self.uiFormatSD.setEnabled(True)
	
	def onHide(self):
		#Hide the feedback only now, rather than timing out. The formatting operation may take a while for larger storage devices, and we don't want to time out the error messages if the operator has stepped away.
		self.uiUSBStorageFeedback.hide()
		self.uiSDStorageFeedback.hide()
	
	
	def ejectUSB(self):
		usbs = [s for s in self.externalStorage if s['interface'] == 'usb']
		
		if not usbs:
			self.uiUSBStorageFeedback.showError('No USB drive recognised.')
		
		for partition in self.externalStorage:
			if partition['interface'] == 'usb':
				api.control('unmount', partition['path'])
	
	def ejectSD(self):
		sds = [s for s in self.externalStorage if s['interface'] == 'sd']
		
		if not sds:
			self.uiSDStorageFeedback.showError('No SD card recognised.')
		
		for partition in self.externalStorage:
			if partition['interface'] == 'sd':
				api.control('unmount', partition['path'])
	
	
	def testNetworkStorage(self):
		self.uiTestNetworkStorage.setEnabled(False)
		self.uiTestNetworkStorageFeedback.showMessage('Connecting…')
		self._testNetworkStorageTimer.start(16*2) #Next frame, hopefully, so the above message displays. The connect call can block for some time.
	
	def finishTestNetworkStorage(self):
		result = api.control('testNetworkStorageCredentials')
		if result:
			self.uiTestNetworkStorageFeedback.showError(result)
		else:
			self.uiTestNetworkStorageFeedback.showMessage('Connection successful.')
		self.uiTestNetworkStorage.setEnabled(True)
	
	@QtCore.pyqtSlot("QVariantList", name="updateMountedDeviceList")
	@api.silenceCallbacks()
	def updateMountedDeviceList(self, externalStorage):
		"""Refresh the "Mounted Devices" display.
			
			We observe externalStorage for this, since it changes
			when the mounted devices change."""
		
		self.externalStorage = externalStorage
		self.uiMountedDeviceList.setText(api.control('df'))