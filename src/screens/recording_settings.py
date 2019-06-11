# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import settings

import api, api2
from api2 import silenceCallbacks


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
		self.window_ = window
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
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
		api.observe('sensorMilliframerate', self.updateMilliframerate)
		
		#Analog gain
		self.populateUiAnalogGain()
		api.observe('recordingAnalogGainMultiplier', self.setAnalogGain)
		self.uiAnalogGain.currentIndexChanged.connect(self.analogGainChanged)
		
		# Button binding.
		self.uiCenterRecording.clicked.connect(self.centerRecording)
		
		self.uiDone.clicked.connect(lambda: window.back())
		
		api.observe('sensorMinExposureNs', self.setMinExposure)
		api.observe('sensorMaxExposureNs', self.setMaxExposure)
		api.observe('recordingExposureNs', self.updateExposure)
		self.uiExposure.valueChanged.connect(
			lambda val: api.set({'recordingExposureNs': val}) )
		self.uiMaximizeExposure.clicked.connect(lambda: 
			self.uiExposure.setValue(self.uiExposure.maximum()) )
		
		self.uiMaximizeFramerate.clicked.connect(lambda: 
			self.uiFps.setValue(self.uiFps.maximum()) )
		
		self.uiSavePreset.clicked.connect(self.savePreset)
		self.uiDeletePreset.clicked.connect(self.deletePreset)
		
		#Finally, sync the presets dropdown with what's displayed.
		self.selectCorrectPreset()
		
		#Hack. Since we set each recording setting individually, we always
		#wind up with a 'custom' entry on our preset list. Now, this might be
		#legitimate - if we're still on Custom by this time, that's just the
		#configuration the camera's in. However, if we're not, we can safely
		#delete it, since it's just a garbage value from the time the second-
		#to-last setting was set during setup.
		if self.uiPresets.itemData(0)['temporary'] and not self.uiPresets.itemData(self.uiPresets.currentIndex())['temporary']:
			self.uiPresets.removeItem(0)
		
		#Set up ui writes after everything is done.
		self.uiHRes.valueChanged.connect(lambda v: api.set({'recordingHRes': v}))
		self.uiVRes.valueChanged.connect(lambda v: api.set({'recordingVRes': v}))
		self.uiHOffset.valueChanged.connect(lambda v: api.set({'recordingHOffset': v}))
		self.uiVOffset.valueChanged.connect(lambda v: api.set({'recordingVOffset': v}))
	
	presets = api.get('commonlySupportedResolutions')
	allRecordingGeometrySettings = ['uiHRes', 'uiVRes', 'uiHOffset', 'uiVOffset', 'uiFps', 'uiFrameDuration']
	
	#The following usually crashes the HDVPSS core, which is responsible for
	#back-of-camera video. (Specifically, in this case, the core crashes if told
	#to render video smaller than 96px tall.) This function was intended to put
	#the recorded image inside the passepartout, to show you what you've got and
	#what you'll be getting.
	def __disabled__onShow(self):
		pos = self.uiPassepartoutInnerBorder.mapToGlobal(
			self.uiPassepartoutInnerBorder.pos() )
		api2.video.call('configure', dump('configure', {
			'xoff': pos.x(),
			'yoff': pos.y(),
			'hres': self.uiPassepartoutInnerBorder.width(),
			'vres': self.uiPassepartoutInnerBorder.height(),
		})).then(api2.video.restart)
	
	
	
	@silenceCallbacks('uiPresets')
	def populatePresets(self):
		formatString = self.uiPresets.currentText()
		self.uiPresets.clear()
		
		for preset in settings.value('customRecordingPresets', []):
			self.uiPresets.insertItem(9999, preset['name'], preset)
		
		#Load from API.
		for preset in self.presets:
			self.uiPresets.insertItem(
				9999,
				formatString % (preset["hRes"], preset["vRes"], preset["framerate"]),
				{
					'custom': False, #Indicates value was saved by user.
					'temporary': False, #Indicates the "custom", the unsaved, preset.
					'values': {
						'uiHRes': preset["hRes"],
						'uiVRes': preset["vRes"],
						'uiFps': preset["framerate"],
					},
				}
			)
	
	
	@silenceCallbacks('uiPresets', *allRecordingGeometrySettings)
	def applyPreset(self, presetNumber: int):
		preset = self.uiPresets.itemData(presetNumber)
		
		#Maximum may be constrained. Disable maximums for preset read-in.
		#Maximums are restored by updateOffsetFromResolution.
		self.uiHOffset.setMaximum(999999)
		self.uiVOffset.setMaximum(999999)
		for key, value in preset['values'].items():
			getattr(self, key).setValue(value)
		
		self.updateOffsetFromResolution()
		preset['custom'] or self.centerRecording() #All non-custom presets are assumed centered.
		self.updatePresetDropdownButtons()
		self.updatePassepartout()
		
	
	def updatePresetDropdownButtons(self):
		if self.uiPresets.currentData()['custom']:
			if self.uiPresets.currentData()['temporary']: #The "Custom" preset. Shows when resolution/offset/framerate do not match a preset.
				self.uiSavePreset.show()
				self.uiDeletePreset.hide()
			else: #Saved presets can be deleted.
				self.uiSavePreset.hide()
				self.uiDeletePreset.show()
		else: 
			self.uiSavePreset.hide()
			self.uiDeletePreset.hide()
	
	
	@silenceCallbacks('uiPresets', *allRecordingGeometrySettings)
	def selectCorrectPreset(self):
		try:
			self.uiPresets.setCurrentIndex(
				[False in [int(getattr(self, (key)).value()) == int(value) for key, value in values.items()] #fail fast, don't check every value. Round to nearest integer because framerate API gets quantized to two places by fps input.
					for values in [ #OK, so problem issss fps is stored different than it's displayed, and with different accuracy.
						self.uiPresets.itemData(index)['values']
						for index in 
						range(self.uiPresets.count())
					]
				].index(False) #index of first item to pass all elem.value() == value tests, ie, matching our preset
			)
		except ValueError:
			#OK, not one of the available presets. (This error should be raised by the final .index() failing to find a match.)
			
			if not self.uiPresets.itemData(0)['temporary']: #Add the "custom" preset if it doesn't exist. This is expected to always be in slot 0.
				self.uiPresets.insertItem(0, 'Custom', {
					'custom': True, #Indicates value was saved by user.
					'temporary': True, #Indicates the "custom", the unsaved, preset.
				})
			
			#Mogrify the custom values to match what is set.
			values = {}
			for elem in self.allRecordingGeometrySettings:
				values[elem] = getattr(self, elem).value()
			
			itemData = self.uiPresets.itemData(0) #read modify write, no in-place merging
			itemData['values'] = values
			self.uiPresets.setItemData(0, itemData)
			
			self.uiPresets.setCurrentIndex(0)
		
		#Check for changes to the save/load preset buttons.
		self.updatePresetDropdownButtons()
	
	
	def savePreset(self):
		itemData = self.uiPresets.currentData()
		itemData['temporary'] = False
		itemData['name'] = f"{self.uiHRes.value()}×{self.uiVRes.value()} @ {int(self.uiFps.value())}fps" #Store name, probably will be editable one day.
		presets = [itemData] + settings.value('customRecordingPresets', [])
		settings.setValue('customRecordingPresets', presets)
		self.uiPresets.setItemData(self.uiPresets.currentIndex(), itemData)
		self.uiPresets.setItemText(self.uiPresets.currentIndex(), itemData['name'])
		
		self.updatePresetDropdownButtons()
	
	@silenceCallbacks('uiPresets') #Don't emit any update signal, we're not changing anything. (Generally, we shouldn't rely on signals to propagate anyway, since that gets very hard to debug very fast.)
	def deletePreset(self, *_):
		settings.setValue('customRecordingPresets', [
			setting
			for setting in settings.value('customRecordingPresets')
			if setting != self.uiPresets.currentData()
		])
		self.uiPresets.removeItem(self.uiPresets.currentIndex())
		self.selectCorrectPreset() #Select Custom again.
	
	
	
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
		self.selectCorrectPreset()
	
	@pyqtSlot(int, name="updateForSensorVOffset")
	@silenceCallbacks()
	def updateForSensorVOffset(self, px: int):
		self.updatePassepartout()
		self.selectCorrectPreset()
	
	@pyqtSlot(int, name="updateForSensorHRes")
	@silenceCallbacks()
	def updateForSensorHRes(self, px: int):
		wasCentered = self.uiHOffset.value() == self.uiHOffset.maximum()//2
		self.uiHOffset.setMaximum(self.uiHRes.maximum() - px) #Can't capture off-sensor.
		wasCentered and self.uiHOffset.setValue(self.uiHOffset.maximum()//2)
		self.updateMaximumFramerate()
		self.updatePassepartout()
		self.selectCorrectPreset()
	
	@pyqtSlot(int, name="updateForSensorVRes")
	@silenceCallbacks()
	def updateForSensorVRes(self, px: int):
		wasCentered = self.uiVOffset.value() == self.uiVOffset.maximum()//2
		self.uiVOffset.setMaximum(self.uiVRes.maximum() - px) #Can't capture off-sensor.
		wasCentered and self.uiVOffset.setValue(self.uiVOffset.maximum()//2)
		self.updateMaximumFramerate()
		self.updatePassepartout()
		self.selectCorrectPreset()
	
	def updateOffsetFromResolution(self):
		self.uiHOffset.setMaximum(self.uiHRes.maximum() - self.uiHRes.value())
		self.uiVOffset.setMaximum(self.uiVRes.maximum() - self.uiVRes.value())
	
	def updateMaximumFramerate(self):
		framerateIsMaxed = self.uiFps.value() == self.uiFps.maximum()
		self.uiFps.setMaximum(
			api.control(
				'framerateForResolution', 
				self.uiHRes.value(),
				self.uiVRes.value() ) )
		if framerateIsMaxed:
			self.uiFps.setValue(self.uiFps.maximum())
	
	
	
	_sensorWidth = api.get('sensorHMax')
	_sensorHeight = api.get('sensorVMax')
	
	def updatePassepartout(self):
		previewTop = 1
		previewLeft = 1
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
			previewLeft,
			previewTop,
			previewWidth - 1,
			passepartoutTop )
		self.uiPassepartoutLeft.setGeometry(
			previewLeft,
			passepartoutTop + 1,
			passepartoutLeft - 1,
			passepartoutHeight - 1 )
		self.uiPassepartoutRight.setGeometry(
			passepartoutLeft + passepartoutWidth + 1,
			passepartoutTop + 1,
			previewWidth - passepartoutLeft - passepartoutWidth - 1,
			passepartoutHeight - 1 )
		self.uiPassepartoutBottom.setGeometry(
			previewLeft,
			passepartoutTop + passepartoutHeight,
			previewWidth - 1,
			previewHeight - passepartoutTop - passepartoutHeight )
		self.uiPassepartoutInnerBorder.setGeometry(
			passepartoutLeft,
			passepartoutTop,
			passepartoutWidth + 1,
			passepartoutHeight + 1 )
	
	
	@pyqtSlot(float, name="updateFps")
	@silenceCallbacks('uiFps', 'uiFrameDuration')
	def updateFps(self, fps: float):
		self.uiFps.setValue(fps)
		self.uiFrameDuration.setValue(1/fps*1000)
		self.selectCorrectPreset()
		api.set({'sensorMilliframerate': int((1/fps*1000)*1e6)})
		
		
	@pyqtSlot(float, name="updateFrameDurationMicroseconds")
	@silenceCallbacks('uiFps', 'uiFrameDuration')
	def updateFrameDurationMicroseconds(self, µs: float):
		self.uiFrameDuration.setValue(µs)
		self.uiFps.setValue(1000/µs)
		self.selectCorrectPreset()
		api.set({'sensorMilliframerate': int((1000/µs)*1e6)})
		
	@pyqtSlot(float, name="updateMilliframerate")
	@silenceCallbacks() #Taken care of by Microsecond version.
	def updateMilliframerate(self, mfps: int):
		print('mfps', mfps)
		self.updateFrameDurationMicroseconds(1e6/(mfps/1000))
		
	
	def centerRecording(self):
		self.uiHOffset.setValue(self.uiHOffset.maximum() // 2)
		self.uiVOffset.setValue(self.uiVOffset.maximum() // 2)
		self.selectCorrectPreset()
		
	
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