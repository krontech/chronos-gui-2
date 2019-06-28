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
	"""Specialised combo box which is autopopulated with mounted partitions."""
	
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
			
		self.clear()
		
		if not partitionList:
			self.setEnabled(False)
			self.addItem(self.tr("no storage found"))
			return
		self.setEnabled(True)
		
		def capturePartitionIndex(i: int): 
			def updateTextWith(space: dict):
				if self.itemData(i):
					if self.itemData(i)["path"] == partitionList[i]["path"]: #Check we're still current after async call.
						self.setItemText(i,
							f"{partitionList[i]['name']} ({round(space['used']/space['available']*100):1.0f}% full)" )
			return updateTextWith
		
		for i in range(len(partitionList)):
			self.addItem(f"{partitionList[i]['name']} (scanning…)", partitionList[i]),
			api.externalPartitions.usageFor(partitionList[i]['device'], capturePartitionIndex(i))