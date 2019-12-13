# -*- coding: future_fstrings -*-
import os
from PyQt5 import uic, QtWidgets, QtCore

import chronosGui2.api as api

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_TriggerDelay
else:
	from chronosGui2.generated.txpro import Ui_TriggerDelay

class TriggerDelay(QtWidgets.QDialog, Ui_TriggerDelay):
	"""Configure how long it takes between IO trigger and action.
		
		Unlike in chronos-cam-app, this screen is *not* responsible
			for keeping the trigger delay set proportionally to the
			length of the recording. It's the responsibility of
			whoever changes the length of the recording. (This could
			reasonable be delegated to the clients or the API.
			Either way, not our problem.)"""
	
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiTriggerDelaySlider.setStyleSheet( #If this turns out to be too expensive to set, just fill in the tip and draw a red rectangle underneath.
			self.uiTriggerDelaySlider.styleSheet() + '\n' + """
				Slider::groove {
					background: qlineargradient( x1:0 y1:0, x2:1 y2:0, stop:0 transparent, stop:0.4999 transparent, stop:0.5001 red, stop:1 red);
				}
			"""
		)
		
		# Value init.
		self.availableDelayMultiplier = 1. #Used for "more" and "less" pre-record delay. Multiplies totalAvailableFrames.
		
		relevantValues = api.getSync(['cameraMaxFrames', 'framePeriod', 'recTrigDelay'] )
		self.cameraMaxFrames = relevantValues['cameraMaxFrames']
		self.framePeriod = relevantValues['framePeriod']
		self.recTrigDelay = relevantValues['recTrigDelay']
		
		api.observe_future_only('cameraMaxFrames', self.updateTotalAvailableFrames)
		api.observe_future_only('framePeriod', self.updateRecordingPeriod)
		api.observe_future_only('recTrigDelay', self.updateTriggerDelay)
		self.updateDisplayedValues()
		
		# Button binding.
		self.ui0Pct.clicked.connect(lambda:
			api.set({'recTrigDelay': 0}) )
		self.ui50Pct.clicked.connect(lambda:
			api.set({'recTrigDelay': self.cameraMaxFrames//2}) )
		self.ui100Pct.clicked.connect(lambda:
			api.set({'recTrigDelay': self.cameraMaxFrames}) )
		
		self.uiTriggerDelaySlider.valueChanged.connect(self.newSliderPosition)
		
		
		self.uiPreRecordDelayFrames.valueChanged.connect(lambda frames:
			api.set({'recTrigDelay': -frames}) )
		self.uiPreRecordDelaySec.valueChanged.connect(lambda seconds:
			api.set({'recTrigDelay': -self.secondsToFrames(seconds)}) )
		
		self.uiPreTriggerRecordingFrames.valueChanged.connect(lambda frames:
			api.set({'recTrigDelay': frames}) )
		self.uiPreTriggerRecordingSec.valueChanged.connect(lambda seconds:
			api.set({'recTrigDelay': self.secondsToFrames(seconds)}) )
		
		self.uiPostTriggerRecordingFrames.valueChanged.connect(lambda frames:
			api.set({'recTrigDelay': self.cameraMaxFrames - frames}) )
		self.uiPostTriggerRecordingSec.valueChanged.connect(lambda seconds:
			api.set({'recTrigDelay': self.cameraMaxFrames - self.secondsToFrames(seconds)}) )
		
		self.uiDone.clicked.connect(window.back)
	
	
	def secondsToFrames(self, seconds: float) -> int:
		return round((seconds*1e9) / self.framePeriod)
	
	def framesToSeconds(self, frames: int) -> float:
		return frames * self.framePeriod / 1e9 #🤞 convert framePeriod to seconds, then multiply to get the duration for frames
	
	
	# @pyqtSlot(int, name="updateTotalAvailableFrames")
	# @silenceCallbacks('uiTriggerDelaySlider')
	def updateTotalAvailableFrames(self, frames: int):
		self.cameraMaxFrames = frames
		self.updateDisplayedValues()
	
	
	# @pyqtSlot(int, name="updateRecordingPeriod")
	# @silenceCallbacks()
	def updateRecordingPeriod(self, frames: int):
		self.framePeriod = frames
		self.updateDisplayedValues()
	
	
	# @pyqtSlot(int, name="updateTriggerDelay")
	# @silenceCallbacks()
	def updateTriggerDelay(self, frames: int):
		self.recTrigDelay = frames
		self.updateDisplayedValues()
	
	
	# @silenceCallbacks('uiTriggerDelaySlider',
	# 	'uiPreRecordDelaySec', 'uiPreTriggerRecordingSec', 'uiPostTriggerRecordingSec',
	# 	'uiPreRecordDelayFrames', 'uiPreTriggerRecordingFrames', 'uiPostTriggerRecordingFrames')
	def updateDisplayedValues(self):
		"""Update all the inputs and values.
			
			This is done as one function because all the inputs are
			displaying the same value, recTrigDelay, so there's no
			real point in separating them. The worst inefficiency is
			when the time-per-frame is changed, since we update 7
			widgets when we could have gotten away with 3. However,
			this is trivial, and we'll end up doing a fair bit of
			updating anyway because these values will often change
			at the same time. The expensive part, painting, will be
			amortized by QT's mark-dirty system."""
		
		self.uiTriggerDelaySlider.setMinimum(round(-self.cameraMaxFrames * self.availableDelayMultiplier))
		self.uiTriggerDelaySlider.setMaximum(self.cameraMaxFrames)
		self.uiTriggerDelaySlider.setPageStep(self.cameraMaxFrames//100)
		self.uiTriggerDelaySlider.setValue(self.recTrigDelay)
		
		
		self.uiPreRecordDelayFrames.setMinimum(0)
		self.uiPreRecordDelayFrames.setMaximum(2**30)
		self.uiPreRecordDelayFrames.setValue(max(0, -self.recTrigDelay))
		
		self.uiPreRecordDelaySec.setMinimum(0)
		self.uiPreRecordDelaySec.setMaximum(
			self.framesToSeconds(self.uiPreRecordDelayFrames.maximum()) )
		self.uiPreRecordDelaySec.setValue(
			self.framesToSeconds(max(0, -self.recTrigDelay)) )
		
		
		self.uiPreTriggerRecordingFrames.setMinimum(0)
		self.uiPreTriggerRecordingFrames.setMaximum(self.cameraMaxFrames)
		self.uiPreTriggerRecordingFrames.setValue(max(0, self.recTrigDelay))
		
		self.uiPreTriggerRecordingSec.setMinimum(0)
		self.uiPreTriggerRecordingSec.setMaximum(
			self.framesToSeconds(self.uiPreTriggerRecordingFrames.maximum()) )
		self.uiPreTriggerRecordingSec.setValue(
			self.framesToSeconds(max(0, self.recTrigDelay)) )
		
		
		self.uiPostTriggerRecordingFrames.setMinimum(0)
		self.uiPostTriggerRecordingFrames.setMaximum(self.cameraMaxFrames)
		self.uiPostTriggerRecordingFrames.setValue(self.cameraMaxFrames-self.recTrigDelay)
		
		self.uiPostTriggerRecordingSec.setMinimum(0)
		self.uiPostTriggerRecordingSec.setMaximum(
			self.framesToSeconds(self.uiPreTriggerRecordingFrames.maximum()) )
		self.uiPostTriggerRecordingSec.setValue(
			self.framesToSeconds(self.cameraMaxFrames-self.recTrigDelay) )
	
	def newSliderPosition(self, recTrigDelay: int):
		# Uncomment this to move the slider and the text at the same time.
		#self.recTrigDelay = recTrigDelay
		#self.updateDisplayedValues()
		
		api.set({'recTrigDelay': recTrigDelay})
		
		#Set the slider label position.
		handleSize = 101 #px
		
		labelSize = self.uiIncomingTrigger.size()
		sliderGeom = self.uiTriggerDelaySlider.geometry()
		sliderPositionX = self.uiTriggerDelaySlider.style().sliderPositionFromValue(self.uiTriggerDelaySlider.minimum(), self.uiTriggerDelaySlider.maximum(), self.uiTriggerDelaySlider.value(), self.uiTriggerDelaySlider.width()-handleSize)
		
		self.uiIncomingTrigger.move(
			min(
				sliderGeom.x()+sliderGeom.width()-labelSize.width(), 
				max(
					sliderPositionX - self.uiIncomingTrigger.width()/2 + handleSize/2 + sliderGeom.x(),
					sliderGeom.x() ) ),
			self.uiIncomingTrigger.pos().y() )
