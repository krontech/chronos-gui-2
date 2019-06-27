# -*- coding: future_fstrings -*-
import os
import subprocess

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot
import logging; log = logging.getLogger('Chronos.gui')

from debugger import *; dbg

import api2 as api


class UpdateFirmware(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/update_firmware.ui", self)
		
		# Panel init.
		self.move(0, 0)
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
	
	def onShow(self):
		api.externalPartitions.observe(self.updateExternalStorageDevices)
	
	def onHide(self):
		api.externalPartitions.unobserve(self.updateExternalStorageDevices)
		
	
	@pyqtSlot('QVariantMap', name="updateExternalStorageDevices")
	def updateExternalStorageDevices(self, partitionList):
		"""Refresh the external storage drop-down list.
			
			Since we know the partition name immediately, that is
			updated first, and then we run the (theoretically, at
			time of writing) async usageFor() query to fill the %
			display."""
			
		self.uiMediaSelect.clear()
		
		if not partitionList:
			self.uiMediaSelect.setEnabled(False)
			self.uiMediaSelect.addItem("«none available»")
			return
		self.uiMediaSelect.setEnabled(True)
		
		def capturePartitionIndex(i: int): 
			def updateTextWith(space: dict):
				if self.uiMediaSelect.itemData(i):
					if self.uiMediaSelect.itemData(i)["path"] == partitionList[i]["path"]: #Check we're still current after async call.
						self.uiMediaSelect.setItemText(i,
							f"{partitionList[i]['name']} ({round(space['used']/space['available']*100):1.0f}% full)" )
			return updateTextWith
		
		for i in range(len(partitionList)):
			self.uiMediaSelect.addItem(f"{partitionList[i]['name']} (scanning…)", partitionList[i]),
			api.externalPartitions.usageFor(partitionList[i]['device'], capturePartitionIndex(i))
	
	
	def saveCameraSettings(self):
		#TODO DDR 2019-06-26: Stop API running here.
		#subprocess.Popen('killall', '-SIGSTOP', ... control and video?
		#Maybe use init.d scripts instead?
		#Restart gui, control, and video after... not sure how to stop this process though, just kill it?
		
		#Calibration data:
		tar = subprocess.Popen('tar', '--create', 
			'--preserve-permissions', '--gzip', '--xattrs',
			'--file', f"{self.uiMediaSelect.currentData()['path'].decode('utf-8')}/chronos_settings.tar",
			#'cal', #Black/white calibration data. #TODO DDR 2019-06-26: Where are the cal files stored?
			'/var/camera/apiConfig.json', #D-Bus API configuration files. (Remember what the last camera settings were.)
			'/root/.config/Krontech', #The settings for this program, the UI.
		) 
		tar.communicate() #fill in .returncode
		if tar.returncode:
			raise Exception(f'tar failed with code {tar.returncode}')
	
	
	def loadCameraSettings(self):
		#TODO DDR 2019-06-26: Stop API running here.
		#subprocess.Popen('killall', '-SIGSTOP', ... control and video?
		#Maybe use init.d scripts instead?
		#Restart gui, control, and video after... not sure how to stop this process though, just kill it?
		tar = subprocess.Popen('tar', '--extract', 
			'--file', f"{self.uiMediaSelect.currentData()['path'].decode('utf-8')}/chronos_settings.tar"
		)
		tar.communicate() #fill in .returncode
		assert tar.returncode is not None
		if tar.returncode:
			raise Exception(f'tar failed with code {tar.returncode}')
		
		bye = subprocess.Popen('shutdown', '--reboot', 'now')
		bye.communicate() #fill in .returncode
		assert bye.returncode is not None
		if bye.returncode:
			raise Exception(f'tar failed with code {tar.returncode}')
		
			
	def applySoftwareUpdate(self):
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