from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks
import format_data


class RecordingSettings(QtWidgets.QDialog):
	"""The recording settings is one of the few windows that doesn't update 
		the camera settings directly. Instead, it has a preview which utilizes
		these settings under the hood, and the settings are actually only
		applied when the "done" button is pressed. The camera is strictly modal
		in its configuration, so there will be some weirdness around this.
	"""
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/recording_settings.ui", self)
		
		self.uiHRes.valueChanged.connect(self.updateForSensorHRes)
	
	@pyqtSlot(int)
	@silenceCallbacks()
	def updateForSensorHRes(self, px: int):
		print('set hr', px)
		self.uiHOffset.setMaximum(self.uiHRes.maximum() - px) #Can't capture off-sensor.
	
	@pyqtSlot(int) #this overwrites the last three functions
	@silenceCallbacks()
	def updateForSensorVRes(self, px: int):
		print('set vr', px)
		self.uiVOffset.setMaximum(self.uiVRes.maximum() - px) #Can't capture off-sensor.