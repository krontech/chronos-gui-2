from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


class TriggerDelay(QtWidgets.QDialog):
	"""Configure how long it takes between IO trigger and action.
		
		Unlike in chronos-cam-app, this screen is *not* responsible
			for keeping the trigger delay set proportionally to the
			length of the recording. It's the responsibility of
			whoever changes the length of the recording. (This could
			reasonable be delegated to the clients or the API.
			Either way, not our problem.)"""
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/trigger_delay.ui", self)
		
		# Panel init.
		self.move(0, 0)
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
		
		relevantValues = api.get(['totalAvailableFrames', 'recordingPeriod', 'triggerDelay'] )
		self.totalAvailableFrames = relevantValues['totalAvailableFrames']
		self.recordingPeriod = relevantValues['recordingPeriod']
		self.triggerDelay = relevantValues['triggerDelay']
		
		api.observe_future_only('totalAvailableFrames', self.updateTotalAvailableFrames)
		api.observe_future_only('recordingPeriod', self.updateRecordingPeriod)
		api.observe_future_only('triggerDelay', self.updateTriggerDelay)
		self.updateDisplayedValues()
		
		# Button binding.
		self.ui0Pct.clicked.connect(lambda:
			api.set({'triggerDelay': 0}) )
		self.ui50Pct.clicked.connect(lambda:
			api.set({'triggerDelay': self.totalAvailableFrames//2}) )
		self.ui100Pct.clicked.connect(lambda:
			api.set({'triggerDelay': self.totalAvailableFrames}) )
		
		self.uiTriggerDelaySlider.valueChanged.connect(self.newSliderPosition)
		
		
		self.uiPreRecordDelayFrames.valueChanged.connect(lambda frames:
			api.set({'triggerDelay': -frames}) )
		self.uiPreRecordDelaySec.valueChanged.connect(lambda seconds:
			api.set({'triggerDelay': -self.secondsToFrames(seconds)}) )
		
		self.uiPreTriggerRecordingFrames.valueChanged.connect(lambda frames:
			api.set({'triggerDelay': frames}) )
		self.uiPreTriggerRecordingSec.valueChanged.connect(lambda seconds:
			api.set({'triggerDelay': self.secondsToFrames(seconds)}) )
		
		self.uiPostTriggerRecordingFrames.valueChanged.connect(lambda frames:
			api.set({'triggerDelay': self.totalAvailableFrames - frames}) )
		self.uiPostTriggerRecordingSec.valueChanged.connect(lambda seconds:
			api.set({'triggerDelay': self.totalAvailableFrames - self.secondsToFrames(seconds)}) )
		
		
		# self.uiDone.clicked.connect(lambda: self and dbg())
		self.uiDone.clicked.connect(window.back)
	
	
	def secondsToFrames(self, seconds: float) -> int:
		return round(seconds / (self.recordingPeriod/1e9))
	
	def framesToSeconds(self, frames: int) -> float:
		return frames * self.recordingPeriod/1e9 #🤞 convert recordingPeriod to seconds, then multiply to get the duration for frames
	
	
	@pyqtSlot(int, name="updateTotalAvailableFrames")
	@silenceCallbacks('uiTriggerDelaySlider')
	def updateTotalAvailableFrames(self, frames: int):
		self.totalAvailableFrames = frames
		self.updateDisplayedValues()
	
	
	@pyqtSlot(int, name="updateRecordingPeriod")
	@silenceCallbacks()
	def updateRecordingPeriod(self, frames: int):
		self.recordingPeriod = frames
		self.updateDisplayedValues()
	
	
	@pyqtSlot(int, name="updateTriggerDelay")
	@silenceCallbacks()
	def updateTriggerDelay(self, frames: int):
		self.triggerDelay = frames
		self.updateDisplayedValues()
	
	
	@silenceCallbacks('uiTriggerDelaySlider',
		'uiPreRecordDelaySec', 'uiPreTriggerRecordingSec', 'uiPostTriggerRecordingSec',
		'uiPreRecordDelayFrames', 'uiPreTriggerRecordingFrames', 'uiPostTriggerRecordingFrames')
	def updateDisplayedValues(self):
		"""Update all the inputs and values.
			
			This is done as one function because all the inputs are
			displaying the same value, triggerDelay, so there's no
			real point in separating them. The worst inefficiency is
			when the time-per-frame is changed, since we update 7
			widgets when we could have gotten away with 3. However,
			this is trivial, and we'll end up doing a fair bit of
			updating anyway because these values will often change
			at the same time. The expensive part, painting, will be
			amortized by QT's mark-dirty system."""
		
		self.uiTriggerDelaySlider.setMinimum(round(-self.totalAvailableFrames * self.availableDelayMultiplier))
		self.uiTriggerDelaySlider.setMaximum(self.totalAvailableFrames)
		self.uiTriggerDelaySlider.setPageStep(self.totalAvailableFrames//100)
		self.uiTriggerDelaySlider.setValue(self.triggerDelay)
		
		
		self.uiPreRecordDelayFrames.setMinimum(0)
		self.uiPreRecordDelayFrames.setMaximum(2**30)
		self.uiPreRecordDelayFrames.setValue(max(0, -self.triggerDelay))
		
		self.uiPreRecordDelaySec.setMinimum(0)
		self.uiPreRecordDelaySec.setMaximum(
			self.framesToSeconds(self.uiPreRecordDelayFrames.maximum()) )
		self.uiPreRecordDelaySec.setValue(
			self.framesToSeconds(max(0, -self.triggerDelay)) )
		
		
		self.uiPreTriggerRecordingFrames.setMinimum(0)
		self.uiPreTriggerRecordingFrames.setMaximum(self.totalAvailableFrames)
		self.uiPreTriggerRecordingFrames.setValue(max(0, self.triggerDelay))
		
		self.uiPreTriggerRecordingSec.setMinimum(0)
		self.uiPreTriggerRecordingSec.setMaximum(
			self.framesToSeconds(self.uiPreTriggerRecordingFrames.maximum()) )
		self.uiPreTriggerRecordingSec.setValue(
			self.framesToSeconds(max(0, self.triggerDelay)) )
		
		
		self.uiPostTriggerRecordingFrames.setMinimum(0)
		self.uiPostTriggerRecordingFrames.setMaximum(self.totalAvailableFrames)
		self.uiPostTriggerRecordingFrames.setValue(self.totalAvailableFrames-self.triggerDelay)
		
		self.uiPostTriggerRecordingSec.setMinimum(0)
		self.uiPostTriggerRecordingSec.setMaximum(
			self.framesToSeconds(self.uiPreTriggerRecordingFrames.maximum()) )
		self.uiPostTriggerRecordingSec.setValue(
			self.framesToSeconds(self.totalAvailableFrames-self.triggerDelay) )
	
	def newSliderPosition(self, triggerDelay: int):
		# Uncomment this to move the slider and the text at the same time.
		#self.triggerDelay = triggerDelay
		#self.updateDisplayedValues()
		
		api.set({'triggerDelay': triggerDelay})
		
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