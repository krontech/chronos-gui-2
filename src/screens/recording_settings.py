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
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiSavePreset.hide()
		
		#Resolution & resolution preview
		
		self.uiHRes.setMinimum(api.get('sensorHMin'))
		self.uiVRes.setMinimum(api.get('sensorVMin'))
		self.uiHRes.setMaximum(api.get('sensorHMax'))
		self.uiVRes.setMaximum(api.get('sensorVMax'))
		self.uiHRes.setSingleStep(api.get('sensorHIncrement'))
		self.uiVRes.setSingleStep(api.get('sensorVIncrement'))
		self.uiHRes.valueChanged.connect(self.updateForSensorHRes)
		self.uiVRes.valueChanged.connect(self.updateForSensorVRes)
		api.observe('recordingHRes', self.updateUiHRes) #DDR 2018-08-28: This screen mostly only updates on "done", since it's using the values it sets to do the preview. Gain being the exception at the moment.
		api.observe('recordingHRes', self.updateForSensorHRes)
		api.observe('recordingVRes', self.updateUiVRes)
		api.observe('recordingVRes', self.updateForSensorVRes)
		
		#Offset min implicit, max set by resolution. Offset set after res because 0 is a good default to set up res at.
		self.uiHOffset.valueChanged.connect(self.updateForSensorHOffset)
		self.uiVOffset.valueChanged.connect(self.updateForSensorVOffset)
		api.observe('recordingHOffset', self.updateUiHOffset) #Originally, this triggered valueChanged which triggered updateForSensorHOffset. However, if h and v were 0, then the change event would never happen since the fields initialize to 0. To fix this, we silence the change events, and bind the passepartout updater functions directly. It's more straightforward, so this isn't necessarily a bad thing.
		api.observe('recordingHOffset', self.updateForSensorHOffset)
		api.observe('recordingVOffset', self.updateUiVOffset)
		api.observe('recordingVOffset', self.updateForSensorVOffset)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)
		self.uiRecordModes.clicked.connect(lambda: window.show('record_mode'))
		
		self.uiMaximizeFramerate.clicked.connect(lambda: 
			self.uiFps.setValue(
				api.control(
					'framerate_for_resolution', 
					self.uiHRes.value(),
					self.uiVRes.value()
				)
			)
		)
		
	
	@pyqtSlot(int)
	@silenceCallbacks('uiHRes')
	def updateUiHRes(self, px: int):
		self.uiHRes.setValue(px)
	
	@pyqtSlot(int)
	@silenceCallbacks('uiVRes')
	def updateUiVRes(self, px: int):
		self.uiVRes.setValue(px)
	
	@pyqtSlot(int)
	@silenceCallbacks('uiHOffset')
	def updateUiHOffset(self, px: int):
		self.uiHOffset.setValue(px)
	
	@pyqtSlot(int)
	@silenceCallbacks('uiVOffset')
	def updateUiVOffset(self, px: int):
		self.uiVOffset.setValue(px)
	
	
	@pyqtSlot(int)
	@silenceCallbacks()
	def updateForSensorHOffset(self, px: int):
		print('set ho', px)
	
	@pyqtSlot(int)
	@silenceCallbacks()
	def updateForSensorVOffset(self, px: int):
		print('set vo', px)
	
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
	
	# sensorHMax
	# sensorHMin
	# sensorVMax
	# sensorVMin
	# sensorHIncrement
	# sensorVIncrement
	
	# recordingHRes
	# recordingVRes
	# recordingHoffset
	# recordingVoffset