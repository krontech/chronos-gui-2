# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg

import api
from api import silenceCallbacks


class UpdateFirmware(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/update_firmware.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		api.observe('externalStorage', self.updateExternalStorageDevices)
		
		# Button binding.
		self.uiSaveCalData.clicked.connect(self.onSaveCalibrationData)
		#No callbacks for changing storage location, it's used to call save cal data with.
		#No callback for safely removing button, we never are in a state where it's unsafe to remove since we always flush the filesystem as part of saving cal data. Kept in because it's comforting… perhaps we should add an affirmative animation, though? 🤔
		
		self.uiApplyUpdate.clicked.connect(self.onApplySoftwareUpdate)
		
		self.uiLoadCalData.clicked.connect(self.onLoadCalibrationData)
		
		self.uiDone.clicked.connect(window.back)
	
	
	@pyqtSlot('QVariantMap', name="updateExternalStorageDevices")
	@silenceCallbacks('uiMediaSelect')
	def updateExternalStorageDevices(self, partitionList):
		"""Refresh the external storage drop-down list."""
		self.uiMediaSelect.clear()
		for p in partitionList:
			self.uiMediaSelect.addItem(
				#f"{p['name']} – {p['free']//(2**30)}GiB/{p['size']//(2**30)}GiB used)", #GiB display seemed a lot clunkier than percentage when I tried it. :/
				'{:s} ({:1.0f}% full)'.format(p["name"], (1-p["free"]/p["size"])*100),
				p["path"] )
	
	
	def onSaveCalibrationData(self):
		error = api.control('saveCalibrationData', self.uiMediaSelect.currentData())
		if error:
			self.uiSaveCalDataError.showError(f'Could not save calibration data: {error["message"]}')
			self.uiLoadCalDataError.hide() #This message overlaps our message. Clear it.
		else:
			self.uiSaveCalDataError.showMessage(f'Saved calibration to external storage.')
			self.uiLoadCalDataError.hide()
	
	def onLoadCalibrationData(self):
		error = api.control('loadCalibrationData', self.uiMediaSelect.currentData())
		if error:
			self.uiLoadCalDataError.showError(f'Could not load calibration data: {error["message"]}')
			self.uiSaveCalDataError.hide()
		else:
			self.uiLoadCalDataError.showMessage(f'Loaded previous calibration.')
			self.uiSaveCalDataError.hide()
			
	def onApplySoftwareUpdate(self):
		error = api.control('applySoftwareUpdate', self.uiMediaSelect.currentData())
		if error:
			self.uiApplyUpdateError.showError(f'Could not apply software update: {error["message"]}')
		else:
			self.uiApplyUpdateError.hide()
	