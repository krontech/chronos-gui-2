from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


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
		self.uiMediaSelect.clear()
		for p in partitionList:
			self.uiMediaSelect.addItem(
				#f"{p['name']} – {p['free']//(2**30)}GiB/{p['size']//(2**30)}GiB used)", #GiB display seemed a lot clunkier than percentage when I tried it. :/
				'{:s} ({:1.0f}% full)'.format(p["name"], (1-p["free"]/p["size"])*100),
				p["path"] )
	
	
	def onSaveCalibrationData(self):
		error = api.control('saveCalibrationData', self.uiMediaSelect.currentData())
		self.uiSaveCalDataError.showMessage(f'Could not save calibration data: {error["message"]}') if error else self.uiSaveCalDataError.hide()
			
	def onApplySoftwareUpdate(self):
		error = api.control('applySoftwareUpdate', self.uiMediaSelect.currentData())
		self.uiApplyUpdateError.showMessage(f'Could not apply software update: {error["message"]}') if error else self.uiApplyUpdateError.hide()
	
	def onLoadCalibrationData(self):
		error = api.control('loadCalibrationData', self.uiMediaSelect.currentData())
		self.uiLoadCalDataError.showMessage(f'Could not load calibration data: {error["message"]}') if error else self.uiLoadCalDataError.hide()
	