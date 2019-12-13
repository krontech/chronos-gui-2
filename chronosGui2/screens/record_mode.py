# -*- coding: future_fstrings -*-
import os
import logging; log = logging.getLogger('Chronos.gui')

from PyQt5 import uic, QtWidgets, QtCore

import chronosGui2.settings as settings
import chronosGui2.api as api

# Import the generated UI form.
from chronosGui2.generated.record_mode import Ui_RecordMode


class RecordMode(QtWidgets.QDialog, Ui_RecordMode):
	
	#Save current screen by ID, not by index or display text because those are UI changes.
	availableRecordModeIds = ['normal', 'segmented', 'burst', 'runAndGun']
	
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Set up panel switching.
		#DDR 2018-07-24: It's impossible to associate an identifier with anything in QT Designer. Painfully load the identifiers here. Also check everything because I will mess this up next time I add a trigger.
		#DDR 2019-08-01: Aaaand the safety check paid off. Told myself.
		if(self.uiRecordMode.count() != len(self.availableRecordModeIds)):
			raise Exception("Record mode screen available record mode IDs does not match the number of textual entries in uiRecordMode.")
		if(self.uiRecordModePanes.count() != len(self.availableRecordModeIds)):
			raise Exception("Record mode screen available record mode IDs does not match the number of uiRecordModePanes panes.")
		
		currentScreenId = settings.value('active record mode', self.availableRecordModeIds[0])
		if(currentScreenId not in self.availableRecordModeIds):
			print(f'{currentScreenId} is not a known record mode ID, defaulting to {self.availableRecordModeIds[0]}')
			currentScreenId = self.availableRecordModeIds[0]
		
		#Disable run-n-gun mode screen until it's added.
		self.uiRecordMode.removeItem(self.availableRecordModeIds.index('runAndGun'))
		
		self.uiRunNGunTimeInSeconds.template = self.uiRunNGunTimeInSeconds.text()
		self.uiRunNGunTimeInFrames.template = self.uiRunNGunTimeInFrames.text()
		self.uiRegularLengthInSeconds.template = self.uiRegularLengthInSeconds.text()
		self.uiRegularLengthInFrames.template = self.uiRegularLengthInFrames.text()
		self.uiBurstTimeInSeconds.template = self.uiBurstTimeInSeconds.text()
		self.uiBurstTimeInFrames.template = self.uiBurstTimeInFrames.text()
		
		# Widget behavour.
		api.observe('recMode', self.setCurrentScreenIndexFromRecordMode)
		self.uiRecordMode.currentIndexChanged.connect(self.changeShownTrigger)
		
		api.observe('cameraMaxFrames', self.recalculateEverything)
		api.observe('recSegments',     self.recalculateEverything)
		api.observe('recMaxFrames',    self.recalculateEverything)
		api.observe('framePeriod',     self.recalculateEverything)
		
		self.uiSegmentLengthInSeconds.valueChanged.connect(lambda sec:
			self.uiSegmentLengthInFrames.setValue(
				int(sec * 1e9 / api.apiValues.get('framePeriod') * api.apiValues.get('recSegments')) ) )
		self.uiSegmentLengthNumSegments.valueChanged.connect(lambda segments:
			api.setSync('recSegments', segments) )
		self.uiSegmentLengthInFrames.valueChanged.connect(lambda frames:
			api.setSync('recMaxFrames', frames * api.apiValues.get('recSegments')) )
		
		self.uiDone.clicked.connect(window.back)
		
	
	def setCurrentScreenIndexFromRecordMode(self, mode):
		self.uiRecordMode.setCurrentIndex(self.availableRecordModeIds.index(mode))
		self.uiRecordModePanes.setCurrentIndex(self.availableRecordModeIds.index(mode))
		
	def changeShownTrigger(self, index):
		self.uiRecordModePanes.setCurrentIndex(index)
		settings.setValue('active record mode', self.availableRecordModeIds[index])
		api.set('recMode', self.availableRecordModeIds[index])
	
	
	def recalculateEverything(self, _):
		segments = api.apiValues.get('recSegments')
		frames = api.apiValues.get('recMaxFrames')
		frameTime = api.apiValues.get('framePeriod')
		totalTime = frames * frameTime / 1e9
		segmentTime = totalTime / segments
		segmentFrames = int(frames / segments)
		maxFrames = api.apiValues.get('cameraMaxFrames')
		segmentMaxFrames = int(maxFrames / segments)
		maxTime = segmentMaxFrames * frameTime / 1e9
		segmentMaxTime = maxTime / segments
		
		self.uiRegularLengthInSeconds.setText(
			self.uiRegularLengthInSeconds.template.format(maxTime) )
		self.uiRegularLengthInFrames.setText(
			self.uiRegularLengthInFrames.template.format(maxFrames) )
		
		self.uiSegmentLengthInSeconds.blockSignals(True)
		self.uiSegmentLengthNumSegments.blockSignals(True)
		self.uiSegmentLengthInFrames.blockSignals(True)
		self.uiSegmentLengthInSeconds.setMaximum(segmentMaxTime)
		self.uiSegmentLengthInSeconds.setValue(segmentTime)
		self.uiSegmentLengthNumSegments.setValue(segments)
		self.uiSegmentLengthInFrames.setMaximum(segmentMaxFrames)
		self.uiSegmentLengthInFrames.setValue(segmentFrames)
		self.uiSegmentLengthInSeconds.blockSignals(False)
		self.uiSegmentLengthNumSegments.blockSignals(False)
		self.uiSegmentLengthInFrames.blockSignals(False)
		
		self.uiBurstTimeInSeconds.setText(
			self.uiBurstTimeInSeconds.template.format(totalTime))
		self.uiBurstTimeInFrames.setText(
			self.uiBurstTimeInFrames.template.format(frames) )