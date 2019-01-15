from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import settings
import api_mock as api
from api_mock import silenceCallbacks



class RecordMode(QtWidgets.QDialog):
	
	#Save current screen by ID, not by index or display text because those are UI changes.
	availableRecordModeIds = ['regular', 'segmented', 'runAndGun']
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/record_mode.ui', self)
		
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Secret high-percision backing value.
		self.nanosegmentLengthPct = 0
		# api.observe('nanosegmentLengthPct', self.updateSegmentLength)
		# api.observe('totalAvailableFrames', )
		# api.observe('recordingExposureNs', )
		
		# Set up panel switching.
		#DDR 2018-07-24 It's impossible to associate an identifier with anything in QT Designer. Painfully load the identifiers here. Also check everything because I will mess this up next time I add a trigger.
		if(self.uiRecordMode.count() != len(self.availableRecordModeIds)):
			raise Exception("Record mode screen available record mode IDs does not match the number of textual entries in uiRecordMode.")
		if(self.uiRecordModePanes.count() != len(self.availableRecordModeIds)):
			raise Exception("Record mode screen available record mode IDs does not match the number of uiRecordModePanes panes.")
		
		currentScreenId = settings.value('active record mode', self.availableRecordModeIds[0])
		if(currentScreenId not in self.availableRecordModeIds):
			print(f'{currentScreenId} is not a known record mode ID, defaulting to {self.availableRecordModeIds[0]}')
			currentScreenId = self.availableRecordModeIds[0]
		
		currentScreenIndex = self.availableRecordModeIds.index(currentScreenId)
		self.uiRecordMode.setCurrentIndex(currentScreenIndex)
		self.changeShownTrigger(currentScreenIndex)
		
		#Disable run-n-gun mode screen until it's added.
		self.uiRecordMode.removeItem(self.availableRecordModeIds.index('runAndGun'))
		
		# Widget behavour.
		self.uiDone.clicked.connect(window.back)
		self.uiRecordMode.currentIndexChanged.connect(self.changeShownTrigger)
		
	def changeShownTrigger(self, index):
		lastModeId = self.availableRecordModeIds[self.uiRecordModePanes.currentIndex()]
		self.uiRecordModePanes.setCurrentIndex(index)
		recordModeID = self.availableRecordModeIds[index]
		settings.setValue('active record mode', recordModeID)
		
		if lastModeId == 'segmented':
			settings.setValue('segmented mode segment duration', )
	
	# @pyqtSlot(int, name="updateSegmentLength")
	# @silenceCallbacks('uiExposureSlider')
	# def updateSegmentLength(self, nanosegmentLengthPct: int):
	# 	lengthPct = nanosegmentLengthPct*1e9
	# 	self.uiSegmentLengthInSeconds.setValue()