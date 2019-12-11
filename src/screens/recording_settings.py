# -*- coding: future_fstrings -*-

from collections import defaultdict
import logging; log = logging.getLogger('Chronos.gui')
from math import floor

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import settings
import api


class RecordingSettings(QtWidgets.QDialog):
	"""The recording settings is one of the few windows that doesn't update 
		the camera settings directly. Instead, it has a preview which utilizes
		these settings under the hood, and the settings are actually only
		applied when the "done" button is pressed. The camera is strictly modal
		in its configuration, so there will be some weirdness around this.
	"""
	
	def __init__(self, window):
		super().__init__()
		if api.apiValues.get('cameraModel')[0:2] == 'TX':
			uic.loadUi("src/screens/recording_settings.txpro.ui", self)
		else:
			uic.loadUi("src/screens/recording_settings.chronos.ui", self)
		self.window_ = window
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		settings.observe('debug controls enabled', False, lambda show:
			self.uiDebug.show() if show else self.uiDebug.hide() )
		self.uiDebug.clicked.connect(lambda: self and dbg())
		
		self.populatePresets()
		self.uiPresets.currentIndexChanged.connect(self.applyPreset)
		
		#Resolution & resolution preview
		invariants = api.getSync([
			'sensorVMax', 'sensorVMin', 'sensorVIncrement',
			'sensorHMax', 'sensorHMin', 'sensorHIncrement',
		])
		self.uiHRes.setMinimum(invariants['sensorHMin'])
		self.uiVRes.setMinimum(invariants['sensorVMin'])
		self.uiHRes.setMaximum(invariants['sensorHMax'])
		self.uiVRes.setMaximum(invariants['sensorVMax'])
		self.uiHRes.setSingleStep(invariants['sensorHIncrement'])
		self.uiVRes.setSingleStep(invariants['sensorVIncrement'])
		
		self.uiHRes.valueChanged.connect(self.updateForSensorHRes)
		self.uiVRes.valueChanged.connect(self.updateForSensorVRes)
		self.uiHOffset.valueChanged.connect(self.updateForSensorHOffset) #Offset min implicit, max set by resolution. Offset set after res because 0 is a good default to set up res at.
		self.uiVOffset.valueChanged.connect(self.updateForSensorVOffset)
		
		self._lastResolution = defaultdict(lambda: None) #Set up for dispatchResolutionUpdate.
		api.observe('resolution', self.dispatchResolutionUpdate)
		

		
		#Frame rate fps/µs binding
		self.uiFps.setMinimum(0.01)
		self.uiFps.valueChanged.connect(self.updateFps)
		self.uiFrameDuration.valueChanged.connect(self.updateFrameDuration)
		api.observe('frameRate', self.updateFpsFromAPI)
		
		#Analog gain
		self.populateUiLuxAnalogGain()
		api.observe('currentGain', self.setLuxAnalogGain)
		self.uiAnalogGain.currentIndexChanged.connect(self.luxAnalogGainChanged)
		
		# Button binding.
		self.uiCenterRecording.clicked.connect(self.centerRecording)
		
		self.uiCancel.clicked.connect(self.revertSettings)
		self.uiDone.clicked.connect(self.applySettings)
		self.uiDone.clicked.connect(lambda: self.window_.back())
		
		api.observe('exposureMin', self.setMinExposure)
		api.observe('exposureMax', self.setMaxExposure)
		api.observe('exposurePeriod', self.updateExposure)
		self.uiExposure.valueChanged.connect(
			lambda val: api.set('exposurePeriod', val) )
		self.uiMaximizeExposure.clicked.connect(lambda: 
			self.uiExposure.setValue(self.uiExposure.maximum()) )
		
		self.uiMaximizeFramerate.clicked.connect(lambda: 
			self.uiFps.setValue(self.uiFps.maximum()) )
		
		self.uiSavePreset.clicked.connect(self.savePreset)
		self.uiDeletePreset.clicked.connect(self.deletePreset)
		
		#Hack. Since we set each recording setting individually, we always
		#wind up with a 'custom' entry on our preset list. Now, this might be
		#legitimate - if we're still on Custom by this time, that's just the
		#configuration the camera's in. However, if we're not, we can safely
		#delete it, since it's just a garbage value from the time the second-
		#to-last setting was set during setup.
		if self.uiPresets.itemData(0)['temporary'] and not self.uiPresets.itemData(self.uiPresets.currentIndex())['temporary']:
			self.uiPresets.removeItem(0)
		
		#Set up ui writes after everything is done.
		self._dirty = False
		self.uiUnsavedChangesWarning.hide()
		self.uiCancel.hide()
		def markDirty(*_):
			self._dirty = True
			self.uiUnsavedChangesWarning.show()
			self.uiCancel.show()
		self.uiHRes.valueChanged.connect(markDirty)
		self.uiVRes.valueChanged.connect(markDirty)
		self.uiHOffset.valueChanged.connect(markDirty)
		self.uiVOffset.valueChanged.connect(markDirty)
	
	__potentialPresetGeometries = [
		[1280, 1024],
		[1280, 720],
		[1280, 512],
		[1280, 360],
		[1280, 240],
		[1280, 120],
		[1280, 96],
		[1024, 768],
		[1024, 576],
		[800, 600],
		[800, 480],
		[640, 480],
		[640, 360],
		[640, 240],
		[640, 120],
		[640, 96],
		[336, 240],
		[336, 120],
		[336, 96],
	]
	presets = []
	for geometry_ in __potentialPresetGeometries: #Fix bug where this overrode the screen's geometry property, preventing any keyboard from opening.
		hRes, vRes = geometry_[0], geometry_[1]
		geometryTimingLimits = api.control.callSync('getResolutionTimingLimits', {'hRes':hRes, 'vRes':vRes})
		if 'error' not in geometryTimingLimits:
			presets += [{
				'hRes': hRes, 
				'vRes': vRes, 
				'framerate': 1e9/geometryTimingLimits['minFramePeriod'],
			}]
		else:
			log.debug(f'Rejected preset resolution {hRes}×{vRes}.')
	
	allRecordingGeometrySettings = ['uiHRes', 'uiVRes', 'uiHOffset', 'uiVOffset', 'uiFps'] #'uiFrameDuration' and 'uiAnalogGain' are not part of the preset, since they're not geometries.
	
	
	#The following usually crashes the HDVPSS core, which is responsible for
	#back-of-camera video. (Specifically, in this case, the core crashes if told
	#to render video smaller than 96px tall.) This function was intended to put
	#the recorded image inside the passepartout, to show you what you've got and
	#what you'll be getting.
	def __disabled__onShow(self):
		pos = self.uiPassepartoutInnerBorder.mapToGlobal(
			self.uiPassepartoutInnerBorder.pos() )
		api.video.call('configure', {
			'xoff': pos.x(),
			'yoff': pos.y(),
			'hres': self.uiPassepartoutInnerBorder.width(),
			'vres': self.uiPassepartoutInnerBorder.height(),
		})
	
	
	def dispatchResolutionUpdate(self, newResolution):
		for key, callbacks in (
			('hRes', [self.updateUiHRes, self.updateForSensorHRes]),
			('vRes', [self.updateUiVRes, self.updateForSensorVRes]),
			('hOffset', [self.updateUiHOffset, self.updateForSensorHOffset]),
			('vOffset', [self.updateUiVOffset, self.updateForSensorVOffset]),
			('minFrameTime', [self.updateMaximumFramerate]),
		):
			if self._lastResolution[key] == newResolution[key]:
				continue
			self._lastResolution[key] = newResolution[key]
			for callback in callbacks:
				callback(newResolution[key])
	
	
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
	
	
	def applyPreset(self, presetNumber: int):
		preset = self.uiPresets.itemData(presetNumber)
		
		#Maximum may be constrained. Disable maximums for preset read-in.
		#Maximums are restored by updateOffsetFromResolution.
		self.uiHOffset.setMaximum(999999)
		self.uiVOffset.setMaximum(999999)
		self.uiFps.setMaximum(999999)
		self.uiFrameDuration.setMinimum(0) #TODO: This gets re-set, right?
		for key, value in preset.get('values', {}).items():
			elem = getattr(self, key)
			elem.blockSignals(True) #Don't fire around a bunch of updates as we set values.
			elem.setValue(value)
			elem.blockSignals(False)
		
		self.updateMaximumFramerate()
		self.updateOffsetFromResolution()
		preset['custom'] or self.centerRecording() #All non-custom presets are assumed centered.
		self.updatePresetDropdownButtons()
		self.updatePassepartout()
		
		#Update frame duration and exposure from frame rate, which we just updated.
		self.uiFrameDuration.setValue(1/self.uiFps.value())
		self.updateExposureLimits()
		
		self._dirty = True
		self.uiUnsavedChangesWarning.show()
		self.uiCancel.show()
		
	
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
	
	
	def selectCorrectPreset(self):
		try:
			self.uiPresets.blockSignals(True) #When selecting a preset, don't try to apply it. This causes framerate to not track to maximum.
			
			#Select the first available preset.
			for index in range(self.uiPresets.count()):
				itemData = self.uiPresets.itemData(index)
				if itemData['temporary']: #Ignore the fake "Custom" preset.
					continue
				
				#Check preset values equal what's on screen. If anything isn't, this isn't our preset index.
				if False in [
					abs(int(getattr(self, key).value()) - int(value)) <= 1
					for key, value in itemData['values'].items()
				]: 
					continue
				
				self.uiPresets.setCurrentIndex(index)
				return
			
			#OK, not one of the available presets.
			#Add the "custom" preset if it doesn't exist. This is expected to always be in slot 0.
			if not self.uiPresets.itemData(0)['temporary']:
				log.print('adding temporary')
				self.uiPresets.insertItem(0, 'Custom', {
					'custom': True, #Indicates value was saved by user.
					'temporary': True, #Indicates the "custom", the unsaved, preset.
				})
			
			#Mogrify the custom values to match what is set.
			itemData = self.uiPresets.itemData(0) #read modify write, no in-place merging
			itemData['values'] = {
				elem: getattr(self, elem).value()
				for elem in self.allRecordingGeometrySettings
			}
			self.uiPresets.setItemData(0, itemData)
			
			#Select the custom preset and check for changes to the save/load preset buttons.
			self.uiPresets.setCurrentIndex(0)
		finally:
			self.updatePresetDropdownButtons()
			self.uiPresets.blockSignals(False)
	
	
	def savePreset(self):
		itemData = self.uiPresets.currentData()
		itemData['temporary'] = False
		itemData['name'] = f"{self.uiHRes.value()}×{self.uiVRes.value()} @ {int(self.uiFps.value())}fps" #Store name, probably will be editable one day.
		presets = [itemData] + settings.value('customRecordingPresets', [])
		settings.setValue('customRecordingPresets', presets)
		self.uiPresets.setItemData(self.uiPresets.currentIndex(), itemData)
		self.uiPresets.setItemText(self.uiPresets.currentIndex(), itemData['name'])
		
		self.updatePresetDropdownButtons()
	
	def deletePreset(self, *_):
		settings.setValue('customRecordingPresets', [
			setting
			for setting in settings.value('customRecordingPresets', [])
			if setting != self.uiPresets.currentData()
		])
		self.uiPresets.removeItem(self.uiPresets.currentIndex())
		self.selectCorrectPreset() #Select Custom again.
	
	
	
	#xywh accessor callbacks, just update the spin box values since these values require a lengthy pipeline rebuild.
	
	@pyqtSlot(int, name="updateUiHRes")
	def updateUiHRes(self, px: int):
		self.uiHRes.setValue(px)
		
	
	@pyqtSlot(int, name="updateUiVRes")
	def updateUiVRes(self, px: int):
		self.uiVRes.setValue(px)
		self.updateMaximumFramerate()
		
	
	@pyqtSlot(int, name="updateUiHOffset")
	def updateUiHOffset(self, px: int):
		self.uiHOffset.setValue(px)
	
	@pyqtSlot(int, name="updateUiVOffset")
	def updateUiVOffset(self, px: int):
		self.uiVOffset.setValue(px)
	
	
	#side-effect callbacks, update everything *but* the spin box values
	@pyqtSlot(int, name="updateForSensorHOffset")
	def updateForSensorHOffset(self, px: int):
		self.updatePassepartout()
		self.selectCorrectPreset()
	
	@pyqtSlot(int, name="updateForSensorVOffset")
	def updateForSensorVOffset(self, px: int):
		self.updatePassepartout()
		self.selectCorrectPreset()
	
	@pyqtSlot(int, name="updateForSensorHRes")
	def updateForSensorHRes(self, px: int):
		wasCentered = self.uiHOffset.value() == self.uiHOffset.maximum()//2
		self.uiHOffset.setMaximum(self.uiHRes.maximum() - px) #Can't capture off-sensor.
		wasCentered and self.uiHOffset.setValue(self.uiHOffset.maximum()//2)
		self.updateMaximumFramerate()
		self.updatePassepartout()
		self.selectCorrectPreset()
	
	@pyqtSlot(int, name="updateForSensorVRes")
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
	
	_lastKnownFramerateOverheadNs = 5000
	def updateMaximumFramerate(self, minFrameTime=None):
		if minFrameTime:
			#Shortcut. We can do this because the exposure values set below by the real call are not required when an API-driven update is fired, since the API-driven update will also update the exposure. I think. 🤞
			limits = {'minFramePeriod': minFrameTime*1e9}
		else:
			limits = api.control.callSync('getResolutionTimingLimits', {
				'hRes': self.uiHRes.value(),
				'vRes': self.uiVRes.value(),
			})
			
			if 'error' in limits:
				log.error(f"Error retrieving maximum framerate for {hRes}×{vRes}: {limits['error']}")
				return
			
			#Note this down for future use by `updateExposureLimits`.
			self._lastKnownFramerateOverheadNs = limits['minFramePeriod'] - limits['exposureMax']
			self.uiExposure.setMinimum(limits['exposureMin'])
		
		log.debug(f"Framerate for {self.uiHRes.value()}×{self.uiVRes.value()}: {1e9 / limits['minFramePeriod']}")
		
		framerateIsMaxed = abs(self.uiFps.maximum() - self.uiFps.value()) <= 1 #There is a bit of uncertainty here, occasionally, of about 0.1 fps.
		self.uiFps.setMaximum(1e9 / limits['minFramePeriod'])
		self.uiFrameDuration.setMinimum(limits['minFramePeriod'] / 1e9) #ns→s
		framerateIsMaxed and self.uiFps.setValue(self.uiFps.maximum())
		framerateIsMaxed and self.uiFrameDuration.setValue(1/self.uiFps.maximum())
		self.updateExposureLimits()
	
	
	_sensorWidth = api.getSync('sensorHMax')
	_sensorHeight = api.getSync('sensorVMax')
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
	def updateFps(self, fps: float):
		self.uiFrameDuration.setValue(1/fps)
		self.selectCorrectPreset()
		self._dirty = True
		self.uiUnsavedChangesWarning.show()
		self.uiCancel.show()
		self.updateExposureLimits()
		
		
	@pyqtSlot(float, name="updateFrameDuration")
	def updateFrameDuration(self, seconds: float):
		self.uiFps.setValue(1/seconds)
		self.selectCorrectPreset()
		self._dirty = True
		self.uiUnsavedChangesWarning.show()
		self.uiCancel.show()
		self.updateExposureLimits()
		
	@pyqtSlot(float, name="updateFpsFromAPI")
	def updateFpsFromAPI(self, fps):
		self.uiFps.setValue(fps)
		self.uiFrameDuration.setValue(1/fps)
		self.selectCorrectPreset()
		self.updateExposureLimits()
	
	
	def updateExposureLimits(self):
		exposureIsMaxed = self.uiExposure.value() == self.uiExposure.maximum()
		self.uiExposure.setMaximum(
			self.uiFrameDuration.value()*1e9 - self._lastKnownFramerateOverheadNs )
		exposureIsMaxed and self.uiExposure.setValue(self.uiExposure.maximum())
		
	
	def centerRecording(self):
		self.uiHOffset.setValue(self.uiHOffset.maximum() // 2)
		self.uiVOffset.setValue(self.uiVOffset.maximum() // 2)
		self.selectCorrectPreset()
		
	
	luxRecordingAnalogGains = [{'multiplier':2**i, 'dB':6*i} for i in range(0,5)]
	
	def populateUiLuxAnalogGain(self):
		formatString = self.uiAnalogGain.currentText()
		self.uiAnalogGain.clear()
		self.uiAnalogGain.insertItems(0, [
			formatString.format(multiplier=gain['multiplier'], dB=gain['dB'])
			for gain in self.luxRecordingAnalogGains
		])
	
	
	def luxAnalogGainChanged(self, index):
		self.uiAnalogGain.setCurrentIndex(index)
		api.set({'currentGain': 
			self.luxRecordingAnalogGains[index]['multiplier']})
	
	@pyqtSlot(int, name="setLuxAnalogGain")
	def setLuxAnalogGain(self, gainMultiplier):
		self.uiAnalogGain.setCurrentIndex(
			list(map(lambda availableGain: availableGain['multiplier'],
				self.luxRecordingAnalogGains))
			.index(floor(gainMultiplier))
		)
	
	@pyqtSlot(int, name="setMaxExposure")
	def setMaxExposure(self, ns):
		self.uiExposure.setMaximum(ns)
	
	@pyqtSlot(int, name="setMinExposure")
	def setMinExposure(self, ns):
		self.uiExposure.setMaximum(ns)
	
	@pyqtSlot(int, name="updateExposure")
	def updateExposure(self, ns):
		self.uiExposure.setValue(ns)
	
	
	def applySettings(self):
		"""Save all setting to the API, which will take some time applying them."""
		
		if self._dirty:
			self._dirty = False
			self.uiUnsavedChangesWarning.hide()
			self.uiCancel.hide()
			api.control.call('set', {
				'resolution': {
					#'vDarkRows': 0, #Don't reset what we don't show. That's annoying if you did manually set it.
					'hRes': self.uiHRes.value(),
					'vRes': self.uiVRes.value(),
					'hOffset': self.uiHOffset.value(),
					'vOffset': self.uiVOffset.value(),
					'minFrameTime': 1/self.uiFps.value(), #This locks the fps in at the lower framerate until you reset it.
				},
				'framePeriod': self.uiFrameDuration.value()*1e9, #s→ns
			})
	
	
	def revertSettings(self):
		"""Set resolution settings back to the API."""
		
		self.updateUiHRes(api.apiValues.get('resolution')['hRes'])
		self.updateUiVRes(api.apiValues.get('resolution')['vRes'])
		self.updateUiHOffset(api.apiValues.get('resolution')['hOffset'])
		self.updateUiVOffset(api.apiValues.get('resolution')['vOffset'])
		self.updateMaximumFramerate(api.apiValues.get('resolution')['minFrameTime'])
		self.updateFpsFromAPI(api.apiValues.get('frameRate'))
		
		self._dirty = False
		self.uiUnsavedChangesWarning.hide()
		self.uiCancel.hide()