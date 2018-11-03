from copy import deepcopy

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


settings = QtCore.QSettings('Krontech', 'back-of-camera interface')

allInputIds = [
	'uiTrigger1Action', 'uiTrigger1ThresholdVoltage', 'uiTrigger11mAPullup', 'uiTrigger120mAPullup', 'uiTrigger1Invert', 'uiTrigger1Debounce',
	'uiTrigger2Action', 'uiTrigger2ThresholdVoltage', 'uiTrigger2Invert', 'uiTrigger2Debounce', 'uiTrigger220mAPullup',
	'uiTrigger3Action', 'uiTrigger3ThresholdVoltage', 'uiTrigger3Invert', 'uiTrigger3Debounce',
	'uiMotionTriggerAction', 'uiMotionTriggerDebounce', 'uiMotionTriggerInvert',
]


class Triggers(QtWidgets.QDialog):
	"""Trigger screen. Configure one IO trigger at a time.
	
		This screen is slightly unusual in that triggers are only
		applied when you hit "apply" or "done", instead of the usual
		apply-on-change. This is because these settings change
		electrical properties, and some configurations - such as
		changing a 1mA pullup to a 20mA pullup - could do physical
		damage. Having to hit another button provides some safety.
		
		Here are some notable variables involved:
			- triggerCapabilities: The properties of the each
				available trigger. Things like what type it is, what
				pullups are available, etc. These only change between
				models of camera, never on an individual camera.
			- triggerConfiguration: How the triggers are set up on
				this camera. When you hit Save or Done, this is what
				is saved.
			- triggerState: Which triggers are currently active. This
				can change extremely frequently, but is only polled
				every so often to avoid network congestion.
		"""
	
	#Save current screen by ID, not by index or display text because those are UI changes.
	#These map IDs to indexes, and must be updated when the .ui file combo box is updated!
	availableTriggerIds = ['trig1', 'trig2', 'trig3', 'motion']
	availableTrigger1Actions = ['none', 'record end', 'exposure gating', 'genlock in', 'genlock out']
	availableTrigger2Actions = ['none', 'record end', 'exposure gating', 'genlock in', 'genlock out']
	availableTrigger3Actions = ['none', 'record end']
	#Analog triggers can take no action.
	availableMotionTriggerActions = ['none', 'record end']
	
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/triggers.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiUnsavedChangesWarning.hide()
		for id in allInputIds:
			obj = getattr(self, id)
			changedSignal = getattr(obj, 'currentIndexChanged', getattr(obj, 'valueChanged', getattr(obj, 'stateChanged', None))) #Couldn't just choose one, could we, QT. 😑
			changedSignal and changedSignal.connect(self.uiUnsavedChangesWarning.show)
		self.uiApply.clicked.connect(self.uiUnsavedChangesWarning.hide)
		self.uiDone.clicked.connect(self.uiUnsavedChangesWarning.hide)
		
		self.trigger3VoltageTextTemplate = self.uiTrigger3ThresholdVoltage.text()
		self.uiTrig1StatusTextTemplate = self.uiTrig1Status.text()
		self.uiTrig2StatusTextTemplate = self.uiTrig2Status.text()
		self.uiTrig3StatusTextTemplate = self.uiTrig3Status.text()
		self.uiMotionTriggerStatusTextTemplate = self.uiMotionTriggerStatus.text()
		
		# Set up panel switching.
		#DDR 2018-07-24 It's impossible to associate an identifier with anything in QT Designer. Painfully load the identifiers here. Also check everything because I will mess this up next time I add a trigger.
		if(self.uiActiveTrigger.count() != len(self.availableTriggerIds)):
			raise Exception("Trigger screen available trigger IDs does not match the number of textual entries in uiActiveTrigger.")
		if(self.uiTriggerScreens.count() != len(self.availableTriggerIds)):
			raise Exception("Trigger screen available trigger IDs does not match the number of uiTriggerScreens screens.")
		
		currentScreenId = settings.value('active trigger', self.availableTriggerIds[0])
		if(currentScreenId not in self.availableTriggerIds):
			print(f'{currentScreenId} is not a known trigger ID, defaulting to {self.availableTriggerIds[0]}')
			currentScreenId = self.availableTriggerIds[0]
		
		currentScreenIndex = self.availableTriggerIds.index(currentScreenId)
		self.uiActiveTrigger.setCurrentIndex(currentScreenIndex)
		self.changeShownTrigger(currentScreenIndex)
		
		self.uiActiveTrigger.currentIndexChanged.connect(self.changeShownTrigger)
		
		#Set up state init & events.
		#self.uiApply.clicked.connect(lambda: self and dbg())
		self.uiApply.clicked.connect(lambda: api.set({
			'triggerConfiguration': self.changedTriggerState()
		}))
		self.uiDone.clicked.connect(lambda: (api.set({
			'triggerConfiguration': self.changedTriggerState()
		}), window.back()))
		
		#OK, so, triggerCapabilities is a constant, that's good. Then
		#we have triggerConfiguration, which is one variable. We'll
		#watch that variable and just update everything when it changes
		#for now. A better way to do it would be to only update state
		#that changed since the last time it updated, so we don't wipe
		#state from unchanged sub-fields. (Note: The reason this is one
		#variable instead of many is that triggers are special, and
		#they need to be updated somewhat atomically. So one variable,
		#so you can't mess it up… I'm not sure this is the best design,
		#but it's what we decided on back when. We do variable
		#change aggregation for the sensor, we could do it here too.
		#But perhaps forcing it safe is a good decision, if less
		#convenient.) So, when *the* state updates, we'll just update
		#everything and it should work for now.
		
		#This shows the three times of data we have. One updates only once, one updates whenever the data is changed, and the final updates every frame.
		self.setCapabilities(api.get('triggerCapabilities'))
		
		self.lastTriggerState = None #Holds the state to update to when we hit save - not everything is directly representable in the interface, so we don't want to round-trip this out into the UI widgets and then back again.
		api.observe('triggerConfiguration', self.updateTriggerConfiguration)
		
		self.triggerStateUpdateTimer = QtCore.QTimer()
		self.triggerStateUpdateTimer.timeout.connect(self.updateTriggerState)
		self.triggerStateUpdateTimer.start(1000/3+0) #Update at 30fps since we're somewhat cpu-bound on this task.
		
		
		def setTrigger1ModifierVisibility(index: int) -> None:
			action = 'hide' if self.availableTrigger1Actions[index] == 'frame sync' else 'show'
			getattr(self.uiTrigger11mAPullup, action)()
			getattr(self.uiTrigger120mAPullup, action)()
			getattr(self.uiTrigger1Debounce, action)()
		self.uiTrigger1Action.currentIndexChanged.connect(setTrigger1ModifierVisibility)
		
		def setTrigger2ModifierVisibility(index: int) -> None:
			action = 'hide' if self.availableTrigger1Actions[index] == 'frame sync' else 'show'
			getattr(self.uiTrigger220mAPullup, action)()
			getattr(self.uiTrigger2Debounce, action)()
		self.uiTrigger2Action.currentIndexChanged.connect(setTrigger2ModifierVisibility)
	
	
	def onShow(self):
		#Don't poll the trigger states while hidden. But do show with accurate info when we start.
		self.updateTriggerState()
		self.triggerStateUpdateTimer.start()
		
	def onHide(self):
		self.triggerStateUpdateTimer.stop()
	
	
	def changeShownTrigger(self, index: int) -> None:
		self.uiTriggerScreens.setCurrentIndex(index)
		settings.setValue('active trigger', self.availableTriggerIds[index])
	
	
	def setCapabilities(self, config: dict) -> None:
		"""Configure the UI with the capabilities reported by the API.
		
			Note: Most of the capabilities are hard-coded into the .ui
			file right now. We only have one camera, so we only have
			one set of capabilities, so it doesn't make a lot of sense
			to pull this out right now.
		"""
		
		self.uiTrigger1ThresholdVoltage.setMinimum(config["trig1"]["thresholdMin"])
		self.uiTrigger1ThresholdVoltage.setMaximum(config["trig1"]["thresholdMax"])
		self.uiTrigger2ThresholdVoltage.setMinimum(config["trig2"]["thresholdMin"])
		self.uiTrigger2ThresholdVoltage.setMaximum(config["trig2"]["thresholdMax"])
	
	
	@pyqtSlot('QVariantMap', name="updateTriggerConfiguration")
	@silenceCallbacks(*allInputIds)
	def updateTriggerConfiguration(self, config: dict) -> None:
		"""Update the displayed trigger settings.
			
			Inverse of changedTriggerState.
			"""
		
		self.lastTriggerState = config #We're currently resetting all our inputs here, so reset trigger state too.
		
		self.uiTrigger1Action.setCurrentIndex(
			self.availableTrigger1Actions.index(config['trig1']['action']) )
		self.uiTrigger1ThresholdVoltage.setValue(config['trig1']['threshold'])
		self.uiTrigger11mAPullup.setChecked(config['trig1']['pullup1ma'])
		self.uiTrigger120mAPullup.setChecked(config['trig1']['pullup20ma'])
		self.uiTrigger1Invert.setChecked(config['trig1']['invert'])
		self.uiTrigger1Debounce.setChecked(config['trig1']['debounce'])
		
		self.uiTrigger2Action.setCurrentIndex(
			self.availableTrigger2Actions.index(config['trig2']['action']) )
		self.uiTrigger2ThresholdVoltage.setValue(config['trig2']['threshold'])
		self.uiTrigger2Invert.setChecked(config['trig2']['invert'])
		self.uiTrigger2Debounce.setChecked(config['trig2']['debounce'])
		self.uiTrigger220mAPullup.setChecked(config['trig2']['pullup20ma'])
		
		self.uiTrigger3Action.setCurrentIndex(
			self.availableTrigger3Actions.index(config['trig3']['action']) )
		self.uiTrigger3ThresholdVoltage.setText(
			self.trigger3VoltageTextTemplate.format(config['trig3']['threshold']) )
		self.uiTrigger3Invert.setChecked(config['trig3']['invert'])
		self.uiTrigger3Debounce.setChecked(config['trig3']['debounce'])
		
		#Most motion trigger settings are displayed in the motion trigger configuration screen.
		self.uiMotionTriggerAction.setCurrentIndex(
			self.availableMotionTriggerActions.index(config['motion']['action']) )
		self.uiMotionTriggerDebounce.setChecked(config['motion']['debounce'])
		self.uiMotionTriggerInvert.setChecked(config['motion']['invert'])
	
	def changedTriggerState(self) -> dict:
		"""Return trigger state, with the modifications made in the UI.
			
			Inverse of updateTriggerConfiguration.
			"""
		
		config = deepcopy(self.lastTriggerState) #Don't mutate the input, keep the model simple.
		
		config['trig1']['action'] = self.availableTrigger1Actions[self.uiTrigger1Action.currentIndex()]
		config['trig1']['threshold'] = self.uiTrigger1ThresholdVoltage.value()
		config['trig1']['pullup1ma'] = self.uiTrigger11mAPullup.checkState() == 2     #0 is unchecked [ ]
		config['trig1']['pullup20ma'] = self.uiTrigger120mAPullup.checkState() == 2   #1 is semi-checked [-]
		config['trig1']['invert'] = self.uiTrigger1Invert.checkState() == 2           #2 is checked [✓]
		config['trig1']['debounce'] = self.uiTrigger1Debounce.checkState() == 2
		
		config['trig2']['action'] = self.availableTrigger2Actions[self.uiTrigger2Action.currentIndex()]
		config['trig2']['threshold'] = self.uiTrigger2ThresholdVoltage.value()
		config['trig2']['invert'] = self.uiTrigger2Invert.checkState() == 2
		config['trig2']['debounce'] = self.uiTrigger2Debounce.checkState() == 2
		config['trig2']['pullup20ma'] = self.uiTrigger220mAPullup.checkState() == 2
		
		config['trig3']['action'] = self.availableTrigger3Actions[self.uiTrigger3Action.currentIndex()]
		config['trig3']['invert'] = self.uiTrigger3Invert.checkState() == 2
		config['trig3']['debounce'] = self.uiTrigger3Debounce.checkState() == 2
		
		#Most motion trigger settings are displayed in the motion trigger configuration screen.
		config['motion']['action'] = self.availableMotionTriggerActions[self.uiMotionTriggerAction.currentIndex()]
		config['motion']['debounce'] = self.uiMotionTriggerDebounce.checkState() == 2
		config['motion']['invert'] = self.uiMotionTriggerInvert.checkState() == 2
		
		return config
	
	
	def updateTriggerState(self):
		state = api.get('triggerState')
		
		self.uiTrig1Status.setText(
			self.uiTrig1StatusTextTemplate
				% ('● high' if state['trig1']['inputIsActive'] else '○ low') )
		self.uiTrig2Status.setText(
			self.uiTrig2StatusTextTemplate
				% ('● high' if state['trig2']['inputIsActive'] else '○ low') )
		self.uiTrig3Status.setText(
			self.uiTrig3StatusTextTemplate
				% ('● high' if state['trig3']['inputIsActive'] else '○ low') )
		self.uiMotionTriggerStatus.setText(
			self.uiMotionTriggerStatusTextTemplate
				% ('● high' if state['motion']['inputIsActive'] else '○ low') )