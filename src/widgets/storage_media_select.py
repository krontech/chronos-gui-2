# -*- coding: future_fstrings -*-

from random import randint
import logging; log = logging.getLogger('Chronos.gui')

from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
from combo_box import ComboBox
try:
	import api2 as api
except Exception:
	#We don't want the lack of an API to fail us in Qt Designer. However, do warn.
	log.warn('Unable to import api, DirectAPILinkPlugin disabled. (Some widgets will not have any effect when used.)')
	api = None

class StorageMediaSelect(ComboBox):
	"""Specialised combo box which is autopopulated with mounted partitions.
		
		The current partition can be retrieved from the data attribute, like:
		`self.uiStorageMediaSelect.currentData()`. This returns a struct like
			
		```python
			{
				'size': 3976200192, 
				'interface': 'other', 
				'path': b'/media/mmcblk1p1', 
				'device': '/org/freedesktop/UDisks2/block_devices/mmcblk1p1', 
				'uuid': '0E7D-5426',
				'name': '4GB Storage Device',
			}
		```"""
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		self.clickMarginColor = f"rgba({randint(128, 255)}, {randint(0, 32)}, {randint(0, 32)}, {randint(64,128)})"
		
		if not api:
			self.setEnabled(False)
			self.addItem('no storage interface')
	
	#Don't subscribe to updates when hidden. (Leads to unneccessary df invocations.)
	def showEvent(self, event):
		api and api.externalPartitions.observe(self.updateExternalStorageDevices)
	
	def hideEvent(self, event):
		api and api.externalPartitions.unobserve(self.updateExternalStorageDevices)
	
	
	@pyqtSlot('QVariantMap', name="updateExternalStorageDevices")
	def updateExternalStorageDevices(self, partitionList):
		"""Refresh the external storage drop-down list.
			
			Since we know the partition name immediately, that is
			updated first, and then we run the (theoretically, at
			time of writing) async usageFor() query to fill the %
			display."""
		
		initialUUID = (self.currentData() or {}).get('uuid') or ''
		initialUUIDs = {
			self.itemData(i)['uuid'] 
			for i in range(self.count())
			if self.itemData(i)
		}
		
		self.clear()
		
		if not partitionList:
			self.setEnabled(False)
			self.addItem(self.tr("no storage found"))
			return
		self.setEnabled(True)
		
		def updateTextFor(i: int): 
			def updateTextWith(space: dict):
				if self.itemData(i):
					if self.itemData(i)["path"] == partitionList[i]["path"]: #Check we're still current after async call.
						self.setItemText(i,
							f"{partitionList[i]['name']} ({round(space['used']/space['available']*100):1.0f}% full)" )
			return updateTextWith
		
		for i in range(len(partitionList)):
			if not partitionList[i]['name']:
				#Use GB rather than GiB. Decided by poll: https://t.me/videografurs/108377
				#partitionList[i]['name'] = f"{partitionList[i]['size'] / 2.**30:1.1f}GiB Storage Device"
				partitionList[i]['name'] = f"{round(partitionList[i]['size'] / 1e9):1.0f}GB Storage Device"
			
			self.addItem(
				f"{partitionList[i]['name']} (scanning…)", 
				partitionList[i],
			),
			api.externalPartitions.usageFor(
				partitionList[i]['device'], 
				updateTextFor(i),
			)
		
		log.print('checking for selection')
		for i in range(len(partitionList)-1, 0-1, -1):
			#Select a new partition, because we probably plugged something in with the intent of using it.
			if partitionList[i]['uuid'] not in initialUUIDs:
				log.print(f"Found new ID {partitionList[i]['name']} / {partitionList[i]['uuid']}")
				self.setCurrentIndex(i)
				return
			
			#If no new partition found, use the current partition.
			if partitionList[i]['uuid'] == initialUUID:
				log.print(f"Using old ID {partitionList[i]['name']} / {partitionList[i]['uuid']}")
				self.setCurrentIndex(i)