# -*- coding: future_fstrings -*-
import re
from os import system

from PyQt5 import uic, QtWidgets, QtCore

from debugger import *; dbg
import api
from external_process import run


class Storage(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		if api.apiValues.get('cameraModel')[0:2] == 'TX':
			uic.loadUi("src/screens/storage.txpro.ui", self)
		else:
			uic.loadUi("src/screens/storage.chronos.ui", self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiFormatMedia.clicked.connect(self.formatMedia)
		self.uiUnmountMedia.clicked.connect(self.unmountMedia)
		
		# Update mounted devices list.
		api.externalPartitions.observe(self.updateMountedDeviceList) #Fast path (only works if partition mountable)
		self._updateMountedDeviceListTimer = QtCore.QTimer() #Slow path, just poll
		self._updateMountedDeviceListTimer.timeout.connect(self.updateMountedDeviceList)
		self._updateMountedDeviceListTimer.setTimerType(QtCore.Qt.VeryCoarseTimer)
		self._updateMountedDeviceListTimer.setInterval(1000)
		
		# Update the dropdown.
		self._lastKnownDevices = None #A list of regex matches. Use .group('name') to get device path name, for example.
		api.externalPartitions.observe(self.pollDevices) #Fast path (only works if partition mountable)
		self._pollDevicesTimer = QtCore.QTimer() #Slow path, just poll
		self._pollDevicesTimer.timeout.connect(self.pollDevices)
		self._pollDevicesTimer.setTimerType(QtCore.Qt.VeryCoarseTimer)
		self._pollDevicesTimer.setInterval(500)
		
		self.uiTestNetworkStorage.clicked.connect(self.testNetworkStorage)
		
		self.uiDone.clicked.connect(window.back)
		
		# Hide network storage until we get SMB working through the API. (pychronos/issues/40)
		self.uiNetworkStoragePanel.hide()
	
	
	def onShow(self):
		self.updateMountedDeviceList()
		self._updateMountedDeviceListTimer.start()
		self.pollDevices()
		self._pollDevicesTimer.start()
	
	def onHide(self):
		self._updateMountedDeviceListTimer.stop()
		self._pollDevicesTimer.stop()
	
	
	def formatMedia(self):
		if not self._lastKnownDevices:
			self.uiLocalMediaFeedback.showError("No devices selected.")
			return
		
		self.uiLocalMediaFeedback.showMessage(
			f"Formatting {self.uiDeviceSelect.currentText()}…")
		
		name = self.uiDeviceSelect.currentData().group('name')
		system(f"umount /dev/{name}*")
		system(f"echo -e \"o\\nn\\n\\n\\n\\n\\nw\\n\" > fdisk /dev/{name}")
		system(f"mkfs.fat -F32 -I -v /dev/{name}*1") #The above doesn't seem to work, so format it again and then it works. \o/
		system(f"fatlabel /dev/{name}*1 \"SLOW VIDEOS\"")
		system(f"mount /dev/{name}*1 /media/{name}1")
		
		#fdisk commands:
		#o↵ #DOS partition table
		#n↵ #new fat partition
		#↵  #defaults, primary, whole thing
		#↵  
		#↵  
		#↵  
		#w↵ #write
		
		#Get partions if last system call fails:
		#['findmnt', f'/dev/{name}', '--raw', '--first-only', '--noheadings', '--output=SOURCE']
		
		self.uiLocalMediaFeedback.showMessage(
			f"{self.uiDeviceSelect.currentText()} is ready to use as SLOW VIDEOS.")
	
	
	def unmountMedia(self):
		if not self._lastKnownDevices:
			self.uiLocalMediaFeedback.showError("No devices selected.")
			return
		
		self.uiLocalMediaFeedback.showMessage(
			f"Ejecting {self.uiDeviceSelect.currentText()}…")
		
		system(f"umount /dev/{self.uiDeviceSelect.currentData().group('name')}*")
		
		self.uiLocalMediaFeedback.showMessage(
			f"It is safe to remove {self.uiDeviceSelect.currentText()}.")
	
	
	def testNetworkStorage(self):
		self.uiNetworkStorageFeedback.showMessage(f'Working…'),
		
		#TODO: This needs to be exposed to the web app, so it needs to go through the API.
		run(self,
			['mount', '-t', 'cifs', '-o', 
				f'user={self.uiNetworkStorageUsername.text()},password={self.uiNetworkStoragePassoword.text()}', 
				f'//{self.uiNetworkStorageAddress.text()}/', '/mnt/cam' ],
			
			lambda exitStatus: 
				self.uiNetworkStorageFeedback.showError(f'Could not connect.'), #Mm, cryptic.
			
			lambda *_:
				self.uiNetworkStorageFeedback.showMessage(
					f'Network storage connected successfully!' ),
		)
	
	
	def updateMountedDeviceList(self, *_):
		"""Refresh the "Mounted Devices" display.
			
			We observe externalStorage for this, since it changes
			when the mounted devices change."""
		
		run(self,
			['df', '--human-readable', 
				'--exclude=tmpfs', '--exclude=devtmpfs', 
				'--output=source,avail,used,pcent,target' ],
			
			lambda exitStatus: 
				self.uiMountedDeviceList.setText(
					f'Could not read storage devices.\n("df" exited with code {exitStatus}.)' ),
			
			self.uiMountedDeviceList.setText,
		)
	
	def pollDevices(self, *_):
		"""Refresh the storage dropdown list with available devices.
			
			Note: We can't use a storageMediaSelect here, because the
				device may not be usable storage media."""
		
		run(self,
			['lsblk', '--pairs', '--output=NAME,SIZE,TYPE'],
			lambda exitStatus: 
				self.uiLocalMediaFeedback.showError(
					f'Could not read storage devices.\n("lsblk" exited with code {exitStatus}.)' ),
			self.pollDevices2 )
		
		#Yields a bunch of lines like:
		#NAME="mmcblk0" SIZE="14.9G" TYPE="disk"
		#NAME="mmcblk0p1" SIZE="39.2M" TYPE="part"
	
	__lsblkRegex = re.compile(r'NAME="(?P<name>.*?)" SIZE="(?P<size>.*?)" TYPE="(?P<type>.*?)"')
	def pollDevices2(self, storageKVPairs: str):
		newDevicesList = [
			match
			for match in [
				self.__lsblkRegex.match(line)
				for line in storageKVPairs.split('\n')
			]
			if match and match.group('type') == 'disk' and match.group('name') != 'mmcblk0' #system disk
		]
		
		if self._lastKnownDevices is not None and (
			[d.group('name')+d.group('size') for d in self._lastKnownDevices] 
			==
			[d.group('name')+d.group('size') for d in newDevicesList]
		):
			return
		
		self._lastKnownDevices = newDevicesList
		
		#Populate the drop-down with the changed media.
		self.uiDeviceSelect.clear()
		if not newDevicesList:
			self.uiDeviceSelect.setDisabled(True)
			self.uiDeviceSelect.insertItem(0, f"No Storage Found")
		else:
			self.uiDeviceSelect.setDisabled(False)
			for device in newDevicesList:
				self.uiDeviceSelect.insertItem(
					0, f"{device.group('size')}B Storage Device", device )