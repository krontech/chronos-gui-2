# -*- coding: future_fstrings -*-

import os
import subprocess
from time import sleep
import logging; log = logging.getLogger('Chronos.gui')

from PyQt5 import uic, QtWidgets, QtCore
from chronosGui2.debugger import *; dbg

import chronosGui2.api as api

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_UpdateFirmware
else:
	from chronosGui2.generated.chronos import Ui_UpdateFirmware

CAM_SERIAL_FILE_NAME = 'cameraSerial.txt'

class UpdateFirmware(QtWidgets.QDialog, Ui_UpdateFirmware):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiMediaSelect.currentIndexChanged.connect(self.uiConfirmRemove.hide)
		self.uiMediaSelect.currentIndexChanged.connect(self.uiApplyUpdateError.hide)
		self.uiSafelyRemove.clicked.connect(self.uiConfirmRemove.showMessage)
		
		# Button binding.
		#No callbacks for changing storage location, it's used to call save cal data with.
		#No callback for safely removing button, we never are in a state where it's unsafe to remove since we always flush the filesystem as part of saving cal data. Kept in because it's comforting… perhaps we should add an affirmative animation, though? 🤔
		self.uiSaveCalData.clicked.connect(self.saveCameraSettings)
		self.uiLoadCalData.clicked.connect(self.loadCameraSettings)
		self.uiApplyUpdate.clicked.connect(self.applySoftwareUpdate)
		self.uiDone.clicked.connect(window.back)
	
	
	def saveCameraSettings(self):
		#TODO DDR 2019-06-26: Stop API running here.
		#subprocess.Popen('killall', '-SIGSTOP', ... control and video?
		#Maybe use init.d scripts instead?
		#Restart gui, control, and video after... not sure how to stop this process though, just kill it?
		#Note: This function is mirrored between update_firmware.py and user_settings.py.
		
		self.uiLoadCalDataError.hide()
		hasattr(self, 'uiFactoryResetError') and self.uiFactoryResetError.hide()
		
		if not self.uiMediaSelect.currentData():
			self.uiSaveCalDataError.showError("Error: No external storage device recognised.")
			return
		
		self.uiSaveCalDataError.showMessage("Working…")
		
		#Bundle up all the configuration files on the camera.
		with open(CAM_SERIAL_FILE_NAME, 'w') as file:
			print(api.apiValues.get('cameraSerial'), end='', file=file, flush=True)
		tar = subprocess.Popen([
			'tar', '--create', '--preserve-permissions', '--gzip', '--xattrs', '--absolute-names',
			'--file', f"{self.uiMediaSelect.currentData()['path'].decode('utf-8')}/chronos_settings.tar",
			CAM_SERIAL_FILE_NAME,
			'/var/camera/cal', #Black/white calibration data. #TODO DDR 2019-06-26: Where are the cal files stored?
			'/var/camera/userFPN', #User-generated calibration data.
			'/var/camera/apiConfig.json', #D-Bus API configuration files. (Remember what the last camera settings were.)
			'/root/.config/Krontech', #The settings for this Python script, the camera UI.
		]) 
		tar.communicate() #fill in .returncode
		assert tar.returncode is not None
		if tar.returncode:
			self.uiSaveCalDataError.showError(f"Error: Could not write \"chronos_settings.tar\" to {self.uiMediaSelect.currentData()['name']}", timeout=0)
			return
		self.uiSaveCalDataError.showMessage('Settings saved to "chronos_settings.tar".')
	
	
	def loadCameraSettings(self):
		#TODO DDR 2019-06-26: Stop API running here.
		#subprocess.Popen('killall', '-SIGSTOP', ... control and video?
		#Maybe use init.d scripts instead?
		#Restart gui, control, and video after... not sure how to stop this process though, just kill it?
		#Note: This function is mirrored between update_firmware.py and user_settings.py.
		
		self.uiSaveCalDataError.hide()
		hasattr(self, 'uiFactoryResetError') and self.uiFactoryResetError.hide()
		
		if not self.uiMediaSelect.currentData():
			self.uiLoadCalDataError.showError("Error: No external storage device recognised.")
			return
		
		self.uiLoadCalDataError.showMessage("Working…")
		
		filePath = f"{self.uiMediaSelect.currentData()['path'].decode('utf-8')}/chronos_settings.tar"
		try:
			onSameCamera = api.apiValues.get('cameraSerial') == str(subprocess.check_output([
				'tar', '--extract', '--to-stdout',
				'--file', filePath, CAM_SERIAL_FILE_NAME,
			]), 'utf-8')
		except subprocess.CalledProcessError:
			self.uiLoadCalDataError.showError(f"Error: No saved settings found on {self.uiMediaSelect.currentData()['name']}.")
			return
		tar = subprocess.Popen([
			'tar', '--extract', '--absolute-names',
			f'--exclude={CAM_SERIAL_FILE_NAME}',
			'--exclude=/var/camera/cal' if not onSameCamera else '',
			'--exclude=/var/camera/userFPN' if not onSameCamera else '',
			'--file', filePath,
		])
		tar.communicate() #fill in .returncode
		assert tar.returncode is not None
		if tar.returncode:
			raise Exception(f'Error: Could not read saved settings from file.')
		
		self.uiLoadCalDataError.showMessage("Settings restored. Restarting camera…")
		for _ in range(10): #DDR 2019-06-27: Repaint screen to show message, I don't know how else to trigger it.
			QtCore.QCoreApplication.processEvents()
		sleep(3)
		
		bye = subprocess.Popen(['shutdown', '--reboot', 'now'])
		bye.communicate() #fill in .returncode
		assert bye.returncode is not None
		if bye.returncode:
			raise Exception(f'system shutdown failed with code {bye.returncode}')
		
			
	def applySoftwareUpdate(self):
		if not self.uiMediaSelect.currentData():
			self.uiApplyUpdateError.showError("Failed to start update: No readable external storage device detected.")
			return
		
		file = self.uiMediaSelect.currentData()["path"] + b"/camUpdate"
		
		if not os.path.isfile(file):
			log.error(f'Failed to start update: Could not find file at {file.decode("utf-8")}.')
			self.uiApplyUpdateError.showError("Could not find update file.")
			return
		
		self.uiApplyUpdateError.showMessage("Working…")
		for _ in range(10): #DDR 2019-06-26: Repaint screen to show message, I don't know how else to trigger it.
			QtCore.QCoreApplication.processEvents()
		
		try:
			os.execle(file, os.environ)
		except OSError as e:
			self.uiApplyUpdateError.showError(f"Update failed: {e}")
