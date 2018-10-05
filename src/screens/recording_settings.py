from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api as api
from api import silenceCallbacks


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
		
		self.populatePresets()
		self.uiPresets.currentIndexChanged.connect(self.applyPreset)
		
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
		
		self.uiHOffset.valueChanged.connect(self.updateForSensorHOffset) #Offset min implicit, max set by resolution. Offset set after res because 0 is a good default to set up res at.
		self.uiVOffset.valueChanged.connect(self.updateForSensorVOffset)
		api.observe('recordingHOffset', self.updateUiHOffset) #Originally, this triggered valueChanged which triggered updateForSensorHOffset. However, if h and v were 0, then the change event would never happen since the fields initialize to 0. To fix this, we silence the change events, and bind the passepartout updater functions directly. It's more straightforward, so this isn't necessarily a bad thing.
		api.observe('recordingHOffset', self.updateForSensorHOffset)
		api.observe('recordingVOffset', self.updateUiVOffset)
		api.observe('recordingVOffset', self.updateForSensorVOffset)
		
		#Frame rate fps/µs binding
		self.uiFps.setMinimum(1e6/api.get('timingMaxExposureNs')) #note: max is min / scale
		self.uiFps.setMaximum(1e6/api.get('timingMinExposureNs'))
		self.uiFrameDuration.setMinimum(api.get('timingMinExposureNs')/1000)
		self.uiFrameDuration.setMaximum(api.get('timingMaxExposureNs')/1000)
		
		self.uiFps.valueChanged.connect(self.updateFps)
		self.uiFrameDuration.valueChanged.connect(self.updateFrameDurationMicroseconds)
		api.observe('recordingExposureNs', self.updateFrameDurationNanoseconds)
		
		#Analog gain
		self.populateUiAnalogGain()
		api.observe('recordingAnalogGainMultiplier', self.setAnalogGain)
		self.uiAnalogGain.currentIndexChanged.connect(self.analogGainChanged)
		
		#Presets
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)
		self.uiRecordModes.clicked.connect(lambda: window.show('record_mode'))
		self.uiCenterRecording.clicked.connect(self.centerRecording)
		
		api.observe('sensorMinExposureNs', self.setMinExposure)
		api.observe('sensorMaxExposureNs', self.setMaxExposure)
		api.observe('recordingExposureNs', self.updateExposure)
		self.uiExposure.valueChanged.connect(
			lambda val: api.set({'recordingExposureNs': val}) )
		self.uiMaximizeExposure.clicked.connect(lambda: 
			self.uiExposure.setValue(self.uiExposure.maximum()) )
		
		self.uiMaximizeFramerate.clicked.connect(lambda: 
			self.uiFps.setValue(self.uiFps.maximum()) )
		
	
	presets = api.get('commonlySupportedResolutions')
	
	def populatePresets(self):
		formatString = self.uiPresets.currentText()
		self.uiPresets.clear()
		self.uiPresets.insertItems(0, [
			formatString % (preset["hRes"], preset["vRes"], preset["framerate"])
			for preset in self.presets
		])
	
	@silenceCallbacks('uiPresets')
	def applyPreset(self, presetNumber: int):
		self.uiPresets.setCurrentIndex(presetNumber)
		preset = self.presets[presetNumber]
		self.uiHRes.setValue(preset["hRes"])
		self.uiVRes.setValue(preset["vRes"])
		self.centerRecording()
		self.uiFps.setValue(self.uiFps.maximum())
		
	
	#xywh accessor callbacks, just update the spin box values since these values require a lengthy pipeline rebuild - and because we're using them for the preview window ;)
	
	@pyqtSlot(int, name="updateUiHRes")
	@silenceCallbacks('uiHRes')
	def updateUiHRes(self, px: int):
		self.uiHRes.setValue(px)
		
	
	@pyqtSlot(int, name="updateUiVRes")
	@silenceCallbacks('uiVRes')
	def updateUiVRes(self, px: int):
		self.uiVRes.setValue(px)
		
	
	@pyqtSlot(int, name="updateUiHOffset")
	@silenceCallbacks('uiHOffset')
	def updateUiHOffset(self, px: int):
		self.uiHOffset.setValue(px)
	
	@pyqtSlot(int, name="updateUiVOffset")
	@silenceCallbacks('uiVOffset')
	def updateUiVOffset(self, px: int):
		self.uiVOffset.setValue(px)
	
	
	#side-effect callbacks, update everything *but* the spin box values
	
	@pyqtSlot(int, name="updateForSensorHOffset")
	@silenceCallbacks()
	def updateForSensorHOffset(self, px: int):
		self.updatePassepartout()
	
	@pyqtSlot(int, name="updateForSensorVOffset")
	@silenceCallbacks()
	def updateForSensorVOffset(self, px: int):
		self.updatePassepartout()
	
	@pyqtSlot(int, name="updateForSensorHRes")
	@silenceCallbacks()
	def updateForSensorHRes(self, px: int):
		wasCentered = self.uiHOffset.value() == self.uiHOffset.maximum()//2
		self.uiHOffset.setMaximum(self.uiHRes.maximum() - px) #Can't capture off-sensor.
		wasCentered and self.uiHOffset.setValue(self.uiHOffset.maximum()//2)
		self.updateMaximumFramerate()
		self.updatePassepartout()
	
	@pyqtSlot(int) #this overwrites the last three functions
	@silenceCallbacks()
	def updateForSensorVRes(self, px: int):
		wasCentered = self.uiVOffset.value() == self.uiVOffset.maximum()//2
		self.uiVOffset.setMaximum(self.uiVRes.maximum() - px) #Can't capture off-sensor.
		wasCentered and self.uiVOffset.setValue(self.uiVOffset.maximum()//2)
		self.updateMaximumFramerate()
		self.updatePassepartout()
		
	
	def updateMaximumFramerate(self):
		framerateIsMaxed = self.uiFps.value() == self.uiFps.maximum()
		self.uiFps.setMaximum(
			api.control(
				'framerate_for_resolution', 
				self.uiHRes.value(),
				self.uiVRes.value() ) )
		if framerateIsMaxed:
			self.uiFps.setValue(self.uiFps.maximum())
	
	
	
	_sensorWidth = api.get('sensorHMax')
	_sensorHeight = api.get('sensorVMax')
	
	def updatePassepartout(self):
		previewTop = 0
		previewLeft = 0
		previewWidth = self.uiPreviewPanel.geometry().right() - self.uiPreviewPanel.geometry().left()
		previewHeight = self.uiPreviewPanel.geometry().bottom() - self.uiPreviewPanel.geometry().top()
		
		recordingTop = self.uiVOffset.value()
		recordingLeft = self.uiHOffset.value()
		recordingRight = self.uiHOffset.value() + self.uiHRes.value()
		recordingBottom = self.uiVOffset.value() + self.uiVRes.value()
		
		passepartoutTop = round(recordingTop / self._sensorHeight * previewHeight)
		passepartoutLeft = round(recordingLeft / self._sensorWidth * previewWidth)
		passepartoutWidth = round((recordingRight - recordingLeft) / self._sensorWidth * previewWidth)
		passepartoutHeight = round((recordingBottom - recordingTop) / self._sensorHeight * previewHeight)
		
		self.uiPassepartoutTop.setGeometry(
			previewLeft+1,
			previewTop+1,
			previewWidth-1,
			passepartoutTop-2 )
		self.uiPassepartoutLeft.setGeometry(
			previewLeft+1,
			passepartoutTop-1,
			passepartoutLeft-2,
			passepartoutHeight+2 )
		self.uiPassepartoutRight.setGeometry(
			passepartoutLeft + passepartoutWidth + 1,
			passepartoutTop-1,
			previewWidth - passepartoutLeft - passepartoutWidth - 1,
			passepartoutHeight+2 )
		self.uiPassepartoutBottom.setGeometry(
			previewLeft+1,
			passepartoutTop + passepartoutHeight + 1,
			previewWidth-1,
			previewHeight - passepartoutTop - passepartoutHeight - 1 )
		self.uiPassepartoutInnerBorder.setGeometry(
			passepartoutLeft-1,
			passepartoutTop-1,
			passepartoutWidth+2,
			passepartoutHeight+2 )
	
	
	@pyqtSlot(float, name="updateFps")
	@silenceCallbacks('uiFps', 'uiFrameDuration')
	def updateFps(self, fps: float):
		self.uiFps.setValue(fps)
		self.uiFrameDuration.setValue(1/fps*1000)
		
	@pyqtSlot(float, name="updateFrameDurationMicroseconds")
	@silenceCallbacks('uiFps', 'uiFrameDuration')
	def updateFrameDurationMicroseconds(self, µs: float):
		self.uiFrameDuration.setValue(µs)
		self.uiFps.setValue(1000/µs)
		
	@pyqtSlot(float, name="updateFrameDurationNanoseconds")
	@silenceCallbacks() #Taken care of by Microsecond version.
	def updateFrameDurationNanoseconds(self, ns: int):
		self.updateFrameDurationMicroseconds(ns/1000)
		
	
	def centerRecording(self):
		self.uiHOffset.setValue(self.uiHOffset.maximum() // 2)
		self.uiVOffset.setValue(self.uiVOffset.maximum() // 2)
		
	
	availableRecordingAnalogGains = api.get('availableRecordingAnalogGains')
	
	def populateUiAnalogGain(self):
		formatString = self.uiAnalogGain.currentText()
		self.uiAnalogGain.clear()
		self.uiAnalogGain.insertItems(0, [
			formatString.format(multiplier=gain["multiplier"], dB=gain["dB"])
			for gain in self.availableRecordingAnalogGains
		])
	
	
	@silenceCallbacks('uiAnalogGain')
	def analogGainChanged(self, index):
		self.uiAnalogGain.setCurrentIndex(index)
		api.set({'recordingAnalogGainMultiplier': 
			self.availableRecordingAnalogGains[index]["multiplier"]})
	
	@pyqtSlot(int, name="setAnalogGain")
	@silenceCallbacks('uiAnalogGain')
	def setAnalogGain(self, gainMultiplier):
		self.uiAnalogGain.setCurrentIndex(
			list(map(lambda availableGain: availableGain["multiplier"],
				self.availableRecordingAnalogGains))
			.index(gainMultiplier)
		)
	
	@pyqtSlot(int, name="setMaxExposure")
	@silenceCallbacks('uiExposure')
	def setMaxExposure(self, ns):
		self.uiExposure.setMaximum(ns)
	
	@pyqtSlot(int, name="setMinExposure")
	@silenceCallbacks('uiExposure')
	def setMinExposure(self, ns):
		self.uiExposure.setMaximum(ns)
	
	@pyqtSlot(int, name="updateExposure")
	@silenceCallbacks('uiExposure')
	def updateExposure(self, ns):
		self.uiExposure.setValue(ns)