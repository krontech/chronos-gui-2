# -*- coding: future_fstrings -*-
"""Trigger/IO Settings screen.
	
	Triggers in the Chronos work as follows: Each action has a few options, such
	as whether to debounce the incoming signal, and one trigger. So, instead of
	saying "When io1 is > 2.5v, stop the recording", you say "Stop the recording
	when io1 is > 2.5v".
	
	This is the inverse of how it works in camApp. Loial completed a rewrite of
	the trigger/io block in 2019, which caused the change, but only gui2 was
	updated to support the full range of functionality this introduced.
	
	To get the data provided by this screen, run either
	
		cam-json --control get - <<< '["ioMapping"]'
	
	or
	
		gdbus call --system \
			--dest ca.krontech.chronos.control \
			--object-path /ca/krontech/chronos/control \
			--method ca.krontech.chronos.control.get \
			"['ioMapping']"
	
	When adding a new option for a trigger, don't forget to…
		- add it to the "resetChanges" function.
		- add it to the "self.markStateDirty" callback list.
		- set up a handler to propagate the changes to self.newIOMapping"""

from copy import deepcopy
from functools import partial
from collections import defaultdict

from PyQt5 import uic, QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSlot, Qt, QItemSelection, QItemSelectionModel
from PyQt5.QtWidgets import QGraphicsOpacityEffect #Also available: QGraphicsBlurEffect, QGraphicsColorizeEffect, QGraphicsDropShadowEffect
from PyQt5.QtGui import QStandardItemModel

from debugger import *; dbg
import settings
import api2
from api import silenceCallbacks

tr = partial(QtCore.QCoreApplication.translate, "Triggers")

#Keep unsaved changes when something else changes them?
KEEP_CHANGES = True
DISCARD_CHANGES = False
updateMode = KEEP_CHANGES

actionData = [
	{ 'id': 'start',       'tags': {'action', 'video', 'edge'},         'name': tr("Start Recording")       },
	{ 'id': 'stop',        'tags': {'action', 'video', 'edge'},         'name': tr("Stop Recording")        },
	{ 'id': 'io1',         'tags': {'action', 'trigger', 'level'},      'name': tr("Output to TRIG1⇄")      },
	{ 'id': 'io2',         'tags': {'action', 'trigger', 'level'},      'name': tr("Output to TRG2⇄")       },
	{ 'id': 'delay',       'tags': {'time', 'level'},                   'name': tr("Delay the Signal")      },
	{ 'id': 'shutter',     'tags': {'action', 'shutter', 'edge'},       'name': tr("Open Shutter")          },
	{ 'id': 'gate',        'tags': {'action', 'shutter', 'level'},      'name': tr("Shutter Gating")        },
	{ 'id': 'combOr1',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block OR #1") },
	{ 'id': 'combOr2',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block OR #2") },
	{ 'id': 'combOr3',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block OR #3") },
	{ 'id': 'combAnd',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block AND")   },
	{ 'id': 'combXOr',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block XOR")   },
	{ 'id': 'toggleClear', 'tags': {'logic', 'toggle', 'edge'},         'name': tr("Turn Flipflop Off")     },
	{ 'id': 'toggleSet',   'tags': {'logic', 'toggle', 'edge'},         'name': tr("Turn Flipflop On")      },
	{ 'id': 'toggleFlip',  'tags': {'logic', 'toggle', 'edge'},         'name': tr("Toggle the Flipflop")   },
]
triggerData = [
	{ 'id': 'none',        'tags': {'constant'},                        'name': { 'whenLevelTriggered': tr("Never"),                          'whenEdgeTriggered': tr("Never")                         } },             
	{ 'id': 'virtual',     'tags': {'emulated', 'software', 'special'}, 'name': { 'whenLevelTriggered': tr("While Record Button Held"),       'whenEdgeTriggered': tr("When Record Button Pressed")    } },               
	{ 'id': 'io1',         'tags': {'io'},                              'name': { 'whenLevelTriggered': tr("While TRIG1⇄ Input"),             'whenEdgeTriggered': tr("On TRIG1⇄ Input")               } },                           
	{ 'id': 'io2',         'tags': {'io'},                              'name': { 'whenLevelTriggered': tr("While TRIG2⇄ Input"),             'whenEdgeTriggered': tr("On TRIG2⇄ Input")               } },                           
	{ 'id': 'io3',         'tags': {'io'},                              'name': { 'whenLevelTriggered': tr("While TRIG3± Input"),             'whenEdgeTriggered': tr("On TRIG3± Input")               } },                           
	{ 'id': 'audio',       'tags': {'disabled'},                        'name': { 'whenLevelTriggered': tr("While Audio Detected"),           'whenEdgeTriggered': tr("When Audio Detected")           } },                                         
	{ 'id': 'motion',      'tags': {'disabled'},                        'name': { 'whenLevelTriggered': tr("While Motion Detected"),          'whenEdgeTriggered': tr("When Motion Detected")          } },                                           
	{ 'id': 'delay',       'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Delayed Signal Arrives"),   'whenEdgeTriggered': tr("When Delayed Signal Arrives")   } },                                                           
	{ 'id': 'comb',        'tags': {'logic', 'combinatorial'},          'name': { 'whenLevelTriggered': tr("While Logic Block Is True"),      'whenEdgeTriggered': tr("When Logic Block Becomes True") } },                                         
	{ 'id': 'toggle',      'tags': {'logic', 'toggle'},                 'name': { 'whenLevelTriggered': tr("While Flipflop On"),              'whenEdgeTriggered': tr("When Flipflop Turns On")        } },                                     
	{ 'id': 'shutter',     'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Shutter Open"),             'whenEdgeTriggered': tr("When Shutter Opens")            } },                                       
	{ 'id': 'recording',   'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Recording"),                'whenEdgeTriggered': tr("When Recording Starts")         } },                                 
	{ 'id': 'dispFrame',   'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When Frame Recorded"),            'whenEdgeTriggered': tr("When Frame Recorded")           } },                                     
	{ 'id': 'startRec',    'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When Recording Starts"),          'whenEdgeTriggered': tr("When Recording Starts")         } },                                       
	{ 'id': 'endRec',      'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When Recording Ends"),            'whenEdgeTriggered': tr("When Recording Ends")           } },                                   
	{ 'id': 'nextSeg',     'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When New Segment"),               'whenEdgeTriggered': tr("When New Segment")              } },                               
	{ 'id': 'timingIo',    'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Timing Signal"),            'whenEdgeTriggered': tr("On Timing Signal")              } },                             
	{ 'id': 'alwaysHigh',  'tags': {'constant'},                        'name': { 'whenLevelTriggered': tr("Always"),                         'whenEdgeTriggered': tr("Once")                          } },               
]



def default(*args):
	for arg in args:
		if arg is not None:
			return arg
	return args[-1]



class TriggersAndIO(QtWidgets.QDialog):
	"""Trigger screen. Configure one IO trigger at a time.
	
		This screen is slightly unusual in that triggers are only
		applied when you hit "apply" or "done", instead of the usual
		apply-on-change. This is because these settings change
		electrical properties, and some configurations - such as
		changing a 1mA pullup to a 20mA pullup - could do physical
		damage. Having to hit another button provides some safety.
		
		Note: There is one trigger which is special. The "virtual"
		trigger is emulated by the UI by setting whatever it's connected
		to to "alwaysHigh" and the "none". This trigger is stored and
		handled by a *completely* separate mechanism than the others."""
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/triggers_and_io.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# State init, screen loads in superposition.
		self.markStateClean()
		#Only needed when trigger for action is set to Never, because the index changed event will never fire then and we'll be stuck with whatever index was set in the .ui file. Ideally, this would not be set in the .ui file in the first place, but realistically since it's set when we change "panels" with the little arrows at the top of the pane we're not gonna remember to clear it every time in the property editor and it'll just be a stupid recurring bug. So fix it here.
		self.uiIndividualTriggerConfigurationPanes.setCurrentIndex(0) 
		
		self.load(actions=actionData, triggers=triggerData)
		
		self.oldIOMapping = defaultdict(lambda: defaultdict(lambda: None)) #Set part and parcel to whatever the most recent mapping is.
		self.newIOMapping = defaultdict(lambda: defaultdict(lambda: None)) #Set piece-by-piece to the new mapping.
		api2.observe('ioMapping', self.onNewIOMapping)
		
		
		self.uiActionList.selectionModel().selectionChanged.connect(
			self.onActionChanged)
		self.uiTriggerList.currentIndexChanged.connect(lambda index:
			self.uiIndividualTriggerConfigurationPanes.setCurrentIndex(
				self.uiTriggerList.itemData(index) ) )
		self.uiActionList.selectionModel().setCurrentIndex(
			self.uiActionList.model().index(0,0),
			QItemSelectionModel.ClearAndSelect )
		
		self.uiTriggerList.currentIndexChanged.connect(self.onTriggerChanged)
		self.uiInvertCondition.stateChanged.connect(self.onInvertChanged)
		self.uiDebounce.stateChanged.connect(self.onDebounceChanged)
		
		#When we change an input, mark the current state dirty until we save.
		self.uiTriggerList   .currentIndexChanged.connect(self.markStateDirty)
		self.uiInvertCondition      .stateChanged.connect(self.markStateDirty)
		self.uiDebounce             .stateChanged.connect(self.markStateDirty)
		self.uiIo1ThresholdVoltage  .valueChanged.connect(self.markStateDirty)
		self.uiIo11MAPullup         .stateChanged.connect(self.markStateDirty)
		self.uiIo120MAPullup        .stateChanged.connect(self.markStateDirty)
		self.uiIo2ThresholdVoltage  .valueChanged.connect(self.markStateDirty)
		self.uiIo220MAPullup        .stateChanged.connect(self.markStateDirty)
		#self.uiAudioTriggerDB      .valueChanged.connect(self.markStateDirty)
		#self.uiAudioTriggerPercent .valueChanged.connect(self.markStateDirty)
		#self.uiAudioTriggerDuration.valueChanged.connect(self.markStateDirty)
		self.uiDelayAmount          .valueChanged.connect(self.markStateDirty)
		
		#Set the appropriate value in the newIOMapping when a custom updates.
		self.uiIo1ThresholdVoltage  .valueChanged.connect(self.onIo1ThresholdVoltageChanged)
		self.uiIo11MAPullup         .stateChanged.connect(self.onIo11MAPullupChanged)
		self.uiIo120MAPullup        .stateChanged.connect(self.onIo120MAPullupChanged)
		self.uiIo2ThresholdVoltage  .valueChanged.connect(self.onIo2ThresholdVoltageChanged)
		self.uiIo220MAPullup        .stateChanged.connect(self.onIo220MAPullupChanged)
		#self.uiAudioTriggerDB      .valueChanged.connect(self.onAudioTriggerDBChanged)
		#self.uiAudioTriggerPercent .valueChanged.connect(self.onAudioTriggerPercentChanged)
		#self.uiAudioTriggerDuration.valueChanged.connect(self.onAudioTriggerDurationChanged)
		self.uiDelayAmount          .valueChanged.connect(self.onDelayAmountChanged)
		
		self.uiSave.clicked.connect(self.saveChanges)
		self.uiCancel.clicked.connect(self.resetChanges)
		self.uiCancel.clicked.connect(self.markStateClean)
		self.uiDone.clicked.connect(window.back)
		
		settings.observe('debug controls enabled', False, lambda show:
			self.uiDebug.show() if show else self.uiDebug.hide() )
		self.uiDebug.clicked.connect(self.debug)
	
	def markStateClean(self):
		self.uiUnsavedChangesWarning.hide()
		self.uiSave.hide()
		self.uiDone.show()
		self.uiCancel.hide()
		
	def markStateDirty(self):
		self.uiUnsavedChangesWarning.show()
		self.uiSave.show()
		self.uiDone.hide()
		self.uiCancel.show()
	
	
	def load(self, actions: list, triggers: list):
		"""Populate the "Action" list and the "Trigger for Action" list.
			
			Does not add any additional data or logic, merely preps."""
		
		assert len(triggers) == self.uiIndividualTriggerConfigurationPanes.count(), \
			f"There must be as many triggers specified in triggers.py ({len(triggers)}) as there are trigger configuration panes in triggers.ui ({self.uiIndividualTriggerConfigurationPanes.count()}). Otherwise, a trigger would be inaccessible or have no screen."
		
		#Populate uiActionList from actions.
		actionListModel = QStandardItemModel(len(actions), 1, self.uiActionList)
		self.uiActionList.setModel(actionListModel)
		for actionIndex in reversed(range(len(actions))):
			if 'disabled' in actions[actionIndex]['tags']:
				actionListModel.removeRow(actionIndex)
			else:
				actionListModel.setItemData(actionListModel.index(actionIndex, 0), {
					Qt.DisplayRole: actions[actionIndex]['name'],
					Qt.UserRole: actionIndex,
					Qt.ForegroundRole: 'red', #Gets set to 'green' or something if trigger is activatable, depending on ioMapping which we don't have yet because of a circular dependency.
					Qt.DecorationRole: None, #Icon would go here.
				})
		
		#Populate uiTriggerList from triggers.
		triggerListModel = self.uiTriggerList.model()
		triggerListModel.insertRows(0, len(triggers))
		for triggerIndex in reversed(range(len(triggers))):
			if 'disabled' in triggers[triggerIndex]['tags']:
				triggerListModel.removeRow(triggerIndex)
			else:
				triggerListModel.setItemData(triggerListModel.index(triggerIndex, 0), {
					Qt.DisplayRole: triggers[triggerIndex]['name']['whenLevelTriggered'],
					Qt.UserRole: triggerIndex,
				})
	
	def resetChanges(self, *_):
		self.newIOMapping = defaultdict(lambda: defaultdict(lambda: None))
		self.onActionChanged(self.uiActionList.selectionModel().selection())
		
		ioMapping = api2.apiValues.get('ioMapping')
		self.uiIo1ThresholdVoltage.setValue(ioMapping['io1In']['threshold'])
		self.uiIo11MAPullup.setChecked(bool(ioMapping['io1']['driveStrength'] & 1))
		self.uiIo120MAPullup.setChecked(bool(ioMapping['io1']['driveStrength'] & 2))
		self.uiIo2ThresholdVoltage.setValue(ioMapping['io2In']['threshold'])
		self.uiIo220MAPullup.setChecked(bool(ioMapping['io2']['driveStrength']))
		#self.uiAudioTriggerDB.setValue(ioMapping[''][''])
		#self.uiAudioTriggerPercent.setValue(ioMapping[''][''])
		#self.uiAudioTriggerDuration.setValue(ioMapping[''][''])
		self.uiDelayAmount.setValue(ioMapping['delay']['delayTime'])
	
	def saveChanges(self, *_):
		ioMapping = api2.apiValues.get('ioMapping')
		api2.set('ioMapping', { #Send along the update delta. Strictly speaking, we could send the whole thing and not a delta, but it seems more correct to only send what we want to change. data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAjCAMAAAApB0NrAAAAdVBMVEUAAAAAFBwCJTYbKjQjOUwoPlI/QT5GTFRDVmVQY3N4XGhgZGbUPobePYXgQY2BZnedZ4GBeH7EYqCXdYjbX5yigJOIjI+NkZTgfai5jZ2gnaHkire6m6fknsPxm8CtsrToqczrr8S9wsTwttHztszzuNPe4N2lYYACAAAAAXRSTlMAQObYZgAAAaBJREFUOMt9kwFTgzAMhVGn4ibMuqql40WFxP//E01TNgpu5o47Lnx9SV9CVS3Dp6iuRVPEZeK1RJrWN43/V+WKWinjg2/zyzUZDxGGvyA0MwkhypC/zHgiFgiqNeObkiGAyXIFo00W3QBdB5h0wWieMtVi7GJ0255XjCcRIR8ABMHh/WOIyEy1ZIRF0Onjhrr+jFbreWZaZGDvemX7n7h7ykxRrDkyCXo3DIOa0+/cw+YddnnvX086XjvBNsbaKfPtNjf3W3xpeuEOhPpt/Nnd98yEt/1LMnE1CO0azkX3eNCqzNBL0Hr31Dp+c5uHu4OoxToMnWr1FwpdrG83qZY5gYkBUMzUd67ew0RERhCMSHgx94A+pcxPQqoG40umBfOYETtPoHwCxf4cNat7ocshpgAUTDY1cD5MYypmTU2qCVHtYEs6B86t2cXUZBYOQRaBUWYPIKPtT26QTufJoMkd8PS1bNNq8Oxkdk3s69HTCdKBnZ0BzU1Q285Ci2mdC6TFn2+3nOpUjo/JyCtMZZNh2+HARUMrSP21/zWMf3V+AVFTVrq9UKSZAAAAAElFTkSuQmCC
			action: {
				key:
					self.newIOMapping[action][key] 
					if self.newIOMapping[action][key] is not None 
					else value
				for key, value in ioMapping[action].items()
			}
			for action, config in self.newIOMapping.items()
			if config
		}).then(self.saveChanges2)
	def saveChanges2(self, *_):
		self.newIOMapping = defaultdict(lambda: defaultdict(lambda: None))
		self.markStateClean()
	
	def onNewIOMapping(self, ioMapping: dict):
		"""Update the IO display with new values, overriding any pending changes."""
		selectedAction = actionData[self.uiActionList.selectionModel().currentIndex().data(Qt.UserRole) or 0]['id']
		
		for action in ioMapping:
			if ioMapping[action] == self.oldIOMapping[action]:
				continue
			
			if updateMode == DISCARD_CHANGES:
				#Override any pending changes to this trigger, since it's been updated elsewhere.
				try: 
					del self.newIOMapping[action]
				except KeyError:
					pass
			
			state = ioMapping[action]
			delta = self.newIOMapping[action]
			#If the trigger is active, update the invert and debounce common conditions.
			if action == selectedAction:
				self.uiInvertCondition.blockSignals(True)
				self.uiInvertCondition.setChecked(bool(default(
					delta['invert'], state['invert'] ))) #tristate checkboxes
				self.uiInvertCondition.blockSignals(False)
				
				self.uiDebounce.blockSignals(True)
				self.uiDebounce.setChecked(bool(default(
					delta['debounce'], state['debounce'] )))
				self.uiDebounce.blockSignals(False)
			
			if action == "io1":
				self.uiIo11MAPullup.setChecked(bool(1 & default(
					delta['driveStrength'], state['driveStrength'] )))
				self.uiIo120MAPullup.setChecked(bool(2 & default(
					delta['driveStrength'], state['driveStrength'] )))
			elif action == "io1In":
				self.uiIo1ThresholdVoltage.setValue(default(
					delta['threshold'], state['threshold'] ))
			elif action == "io2":
				self.uiIo220MAPullup.setChecked(bool(default(
					delta['driveStrength'], state['driveStrength'] )))
			elif action == "io2In":
				self.uiIo2ThresholdVoltage.setValue(default(
					delta['threshold'], state['threshold'] ))
			elif action == "delay":
				self.uiDelayAmount.setValue(default(
					delta['delayTime'], state['delayTime'] ))
		
		self.oldIOMapping = ioMapping
		
		#Check if all operator changes have been overwritten by updates.
		if not (value for value in self.newIOMapping if value):
			self.markStateClean()
	
	
	def onActionChanged(self, selected: QItemSelection, deselected: QItemSelection = []):
		"""Update the UI when the selected action is changed.
			
			This function updates the trigger list, invert,
				and debounce elements. The trigger list will
				sync the active configuration pane, because
				it needs to do that anyway when the operator
				changes the trigger."""
		
		action = actionData[selected.indexes()[0].data(Qt.UserRole)]
		config = api2.apiValues.get('ioMapping')[action['id']]
		newConfig = self.newIOMapping[action['id']]
		dataIndex = [trigger['id'] for trigger in triggerData].index(newConfig['source'] or config['source'])
		
		listIndex = self.uiTriggerList.findData(dataIndex)
		assert listIndex is not -1, f"Could not find index for {config['source']} ({dataIndex}) in uiTriggerList."
		self.uiTriggerList.setCurrentIndex(listIndex)
		
		self.uiInvertCondition.blockSignals(True) #We can block these signals because nothing else depends on them. A few things depend on the Trigger for Action combobox, so it is just a little smarter about it's updates to deal with this changing.
		self.uiInvertCondition.setChecked(bool(default(
			newConfig['invert'], config['invert'] )))
		self.uiInvertCondition.blockSignals(False)
		
		self.uiDebounce.blockSignals(True)
		self.uiDebounce.setChecked(bool(default(
			newConfig['debounce'], config['debounce'] )))
		self.uiDebounce.blockSignals(False)
		
		#Update action label text for action level/edge triggering.
		assert ('level' in action['tags']) != ('edge' in action['tags']), f"actionData['{action['id']}'] needs to be tagged as either 'level' or 'edge' triggered."
		if not deselected or not deselected.indexes():
			return
		if 'level' in action['tags'] == 'level' in actionData[deselected.indexes()[0].data(Qt.UserRole)]['tags']:
			return
		
		whenLevelOrEdge = 'whenLevelTriggered' if 'level' in action['tags'] else 'whenEdgeTriggered'
		for triggerListIndex in range(self.uiTriggerList.count()):
			triggerDataIndex = self.uiTriggerList.itemData(triggerListIndex)
			self.uiTriggerList.setItemText(triggerListIndex,
				triggerData[triggerDataIndex]['name'][whenLevelOrEdge] )
	
	
	def onTriggerChanged(self, index: int):
		activeAction = actionData[self.uiActionList.selectionModel().currentIndex().data(Qt.UserRole)]
		newSource = triggerData[self.uiTriggerList.itemData(index)]['id']
		activeMapping = self.newIOMapping[activeAction['id']]
		if api2.apiValues.get('ioMapping')[activeAction['id']]['source'] == newSource:
			if activeMapping['source']: #Clear key if it exists, no need to set. Otherwise, when we switched actions, the trigger would always get set to what it was, which is pointless.
				del activeMapping['source']
		else:
			activeMapping['source'] = triggerData[self.uiTriggerList.itemData(index)]['id']
	
	def onInvertChanged(self, state: int):
		activeAction = actionData[self.uiActionList.selectionModel().currentIndex().data(Qt.UserRole)]
		self.newIOMapping[activeAction['id']]['invert'] = bool(state)
	
	def onDebounceChanged(self, state: int):
		activeAction = actionData[self.uiActionList.selectionModel().currentIndex().data(Qt.UserRole)]
		self.newIOMapping[activeAction['id']]['debounce'] = bool(state)
	
	
	def onIo1ThresholdVoltageChanged(self, value: float):
		self.newIOMapping['io1In']['threshold'] = value
	
	def onIo11MAPullupChanged(self, state: int):
		self.newIOMapping['io1']['driveStrength'] = bool(state) + self.uiIo120MAPullup.checkState()
	
	def onIo120MAPullupChanged(self, state: int):
		self.newIOMapping['io1']['driveStrength'] = self.uiIo11MAPullup.isChecked() + state
	
	def onIo2ThresholdVoltageChanged(self, value: float):
		self.newIOMapping['io2In']['threshold'] = value
	
	def onIo220MAPullupChanged(self, state: int):
		self.newIOMapping['io2']['driveStrength'] = int(bool(state))
	
	def onAudioTriggerDBChanged(self, value: float):
		raise NotImplementedError()
	
	def onAudioTriggerPercentChanged(self, value: float):
		raise NotImplementedError()
	
	def onAudioTriggerDurationChanged(self, value: float):
		raise NotImplementedError()
	
	def onDelayAmountChanged(self, value: float):
		self.newIOMapping['delay']['delayTime'] = value
	
	
	def debug(self, *_):
		print()
		print()
		print('existing:')
		pp(api2.apiValues.get('ioMapping'))
		print()
		print('pending:')
		pp(self.newIOMapping)
		print()
		dbg()
		





allInputIds = (
	'uiTrigger1Action', 'uiTrigger1ThresholdVoltage', 'uiTrigger11mAPullup', 'uiTrigger120mAPullup', 'uiTrigger1Invert', 'uiTrigger1Debounce',
	'uiTrigger2Action', 'uiTrigger2ThresholdVoltage', 'uiTrigger2Invert', 'uiTrigger2Debounce', 'uiTrigger220mAPullup',
	'uiTrigger3Action', 'uiTrigger3ThresholdVoltage', 'uiTrigger3Invert', 'uiTrigger3Debounce',
	'uiMotionTriggerAction', 'uiMotionTriggerDebounce', 'uiMotionTriggerInvert',
)

visualizationPadding = (15, 20, 0, 20) #top, right, bottom, left; like CSS

highStrength = 1.0
lowStrength = 0.5

#Old-style triggers. Obsolete, rewritten by otters.
#Grab a working copy with: git checkout tags/old-triggers
class TriggersOld(QtWidgets.QDialog):
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
	availableTriggerIds = ('trig1', 'trig2', 'trig3', 'motion')
	availableTrigger1Actions = ('none', 'record end', 'exposure gating', 'genlock in', 'genlock out')
	availableTrigger2Actions = ('none', 'record end', 'exposure gating', 'genlock in', 'genlock out')
	availableTrigger3Actions = ('none', 'record end')
	availableAnalog1Actions = ('none') #Analog triggers will be able to take action in the next version of triggers.
	availableAnalog2Actions = ('none') 
	availableMotionTriggerActions = ('none', 'record end')
	
	#Signals don't get to be debounced, that only applies to level-based triggers.
	signalBasedTriggers = ('exposure gating', 'genlock in', 'genlock out')
	
	#Output triggers are visualized differently than input triggers. They don't listen, they tell; so they output to their trigger instead of taking it as input.
	outputTriggers = ('genlock out')
	
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/triggers.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		for id in allInputIds:
			obj = getattr(self, id)
			changedSignal = getattr(obj, 'currentIndexChanged', getattr(obj, 'valueChanged', getattr(obj, 'stateChanged', None))) #Couldn't just choose one, could we, QT. 😑
			changedSignal and changedSignal.connect(self.queueVisualizationRepaint)
			changedSignal and changedSignal.connect(self.markStateDirty)
		
		self.markStateClean() #Initialize. Comes in dirty from Qt Creator.
		self.uiSave.clicked.connect(self.markStateClean)
		self.uiCancel.clicked.connect(self.markStateClean)
		
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
		
		#We don't have motion triggering working yet, so we'll just remove it here…
		if currentScreenId != 'motion':
			self.uiActiveTrigger.removeItem(self.availableTriggerIds.index('motion'))
		
		#Set up state init & events.
		#self.uiSave.clicked.connect(lambda: self and dbg()) #Debug! \o/
		self.uiSave.clicked.connect(lambda: api.set({
			'triggerConfiguration': self.changedTriggerState()
		}))
		self.uiDone.clicked.connect(window.back)
		self.uiCancel.clicked.connect(lambda: 
			self.updateTriggerConfiguration(self.lastTriggerConfiguration))
		
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
		
		self.lastTriggerConfiguration = None #Holds the state to update to when we hit save - not everything is directly representable in the interface, so we don't want to round-trip this out into the UI widgets and then back again.
		api.observe('triggerConfiguration', self.updateTriggerConfiguration)
		
		self.lastTriggerState = None
		
		#Set up the little fade effect on the trigger icons, indicating high and low.
		self.trigger1IconLevelEffect = QGraphicsOpacityEffect(self.uiTrigger1Icon)
		self.trigger2IconLevelEffect = QGraphicsOpacityEffect(self.uiTrigger2Icon)
		self.trigger3IconLevelEffect = QGraphicsOpacityEffect(self.uiTrigger3Icon)
		self.motionTriggerIconLevelEffect = QGraphicsOpacityEffect(self.uiMotionTriggerIcon)
		
		#self.uiTrigger1Icon.setGraphicsEffect(self.trigger1IconLevelEffect)
		#self.uiTrigger2Icon.setGraphicsEffect(self.trigger2IconLevelEffect)
		#self.uiTrigger3Icon.setGraphicsEffect(self.trigger3IconLevelEffect)
		#self.uiMotionTriggerIcon.setGraphicsEffect(self.motionTriggerIconLevelEffect)
		
		self.uiTrigger1Visualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiTrigger1Visualization, evt, 'trig1'))
		self.uiTrigger2Visualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiTrigger2Visualization, evt, 'trig2'))
		self.uiTrigger3Visualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiTrigger3Visualization, evt, 'trig3'))
		self.uiMotionTriggerVisualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiMotionTriggerVisualization, evt, 'motion'))
		
		self.triggerStateUpdateTimer = QtCore.QTimer()
		self.triggerStateUpdateTimer.timeout.connect(self.updateTriggerState)
		self.triggerStateUpdateTimer.setInterval(1000/3+0) #Update at 30fps since we're somewhat cpu-bound on this task.
		
		def setTrigger1ModifierVisibility(index: int) -> None:
			action = 'hide' if self.availableTrigger1Actions[index] in self.signalBasedTriggers else 'show'
			getattr(self.uiTrigger1Debounce, action)()
		self.uiTrigger1Action.currentIndexChanged.connect(setTrigger1ModifierVisibility)
		
		def setTrigger2ModifierVisibility(index: int) -> None:
			action = 'hide' if self.availableTrigger1Actions[index] in self.signalBasedTriggers else 'show'
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
		
		self.lastTriggerConfiguration = config #We're currently resetting all our inputs here, so reset trigger state too.
		
		self.uiTrigger1Action.setCurrentIndex(
			self.availableTrigger1Actions.index(config['trig1']['action']) )
		self.uiTrigger1ThresholdVoltage.setValue(config['trig1']['threshold'])
		self.uiTrigger11mAPullup.setChecked(config['trig1']['pullup1ma'])
		self.uiTrigger120mAPullup.setChecked(config['trig1']['pullup20ma'])
		self.uiTrigger1Invert.setChecked(config['trig1']['invert'])
		self.uiTrigger1Debounce.setChecked(config['trig1']['debounce'])
		self.uiTrigger1Debounce.setVisible(
			config['trig1']['action'] not in self.signalBasedTriggers )
		
		self.uiTrigger2Action.setCurrentIndex(
			self.availableTrigger2Actions.index(config['trig2']['action']) )
		self.uiTrigger2ThresholdVoltage.setValue(config['trig2']['threshold'])
		self.uiTrigger2Invert.setChecked(config['trig2']['invert'])
		self.uiTrigger2Debounce.setChecked(config['trig2']['debounce'])
		self.uiTrigger220mAPullup.setChecked(config['trig2']['pullup20ma'])
		self.uiTrigger2Debounce.setVisible(
			config['trig2']['action'] not in self.signalBasedTriggers )
		
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
		
		config = deepcopy(self.lastTriggerConfiguration) #Don't mutate the input, keep the model simple.
		
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
		if state == self.lastTriggerState:
			return #No action needed, nothing changed.
		self.lastTriggerState = state
		
		#Set trigger status indicators.
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
		
		#Set trigger icon effect.
		self.trigger1IconLevelEffect.setOpacity(highStrength if state['trig1']['inputIsActive'] else lowStrength)
		self.trigger2IconLevelEffect.setOpacity(highStrength if state['trig2']['inputIsActive'] else lowStrength)
		self.trigger3IconLevelEffect.setOpacity(highStrength if state['trig3']['inputIsActive'] else lowStrength)
		self.motionTriggerIconLevelEffect.setOpacity(highStrength if state['motion']['inputIsActive'] else lowStrength)
		
		#Mark visualization panes dirty, so they update appropriately.
		self.queueVisualizationRepaint()
	
	def markStateClean(self):
		self.uiUnsavedChangesWarning.hide()
		self.uiSave.hide()
		self.uiDone.show()
		self.uiCancel.hide()
		
	def markStateDirty(self):
		self.uiUnsavedChangesWarning.show()
		self.uiSave.show()
		self.uiDone.hide()
		self.uiCancel.show()
	
	def queueVisualizationRepaint(self):
		self.uiTrigger1Visualization.update()
		self.uiTrigger2Visualization.update()
		self.uiTrigger3Visualization.update()
		self.uiMotionTriggerVisualization.update()
	
	def paintVisualization(self, pane, event, triggerId):
		"""Paint the trigger level visualization pane.
			
			If the element + padding (which includes arrows) is wider
			than the remaining space, loop back to a new line. For each
			step of the process, highlight (or not) the trigger level.
			"""
		
		#print('paint', pane, event)
		#QPixmap("../../assets/qt_creator/check_box.svg")
		QPainter = QtGui.QPainter
		QPen = QtGui.QPen
		QPoint = QtCore.QPoint
		QColor = QtGui.QColor
		QFont = QtGui.QFont
		QPainterPath = QtGui.QPainterPath
		QImage = QtGui.QImage
		Qt = QtCore.Qt
		
		tinyFont = QFont("DejaVu Sans", 9, weight=QtGui.QFont.Thin)
		normalFont = QFont("DejaVu Sans", 11, weight=QtGui.QFont.Thin)
		
		visWidth = event.rect().width()
		
		#Output is assumed to always be high, so just always draw it black. There's some more work that needs to be done here.
		#Basically, we need a state that shows that something is a ~waveform~, not a level-based trigger. (eg, high/low)
		#We don't really have that at the moment, aside from "flickering madly".
		isOutputTrigger = False
		
		def strength(triggerIsActive: bool) -> float:
			return (
				highStrength 
				if triggerIsActive or isOutputTrigger else
				lowStrength
			)
		
		triggerState = self.lastTriggerState[triggerId]
		triggerIsActive = triggerState["inputIsActive"]
		
		painter = QPainter(pane)
		
		painter.setRenderHint(QPainter.Antialiasing, True)
		painter.setRenderHint(QPainter.TextAntialiasing, True)
		
		pen = QPen(QColor(0), 1, join=Qt.MiterJoin) #Miter join makes arrows look good.
		painter.setPen(pen)
		
		#x and y are the layout cursor. If we don't have enough room on a line (all elements are fixed-width) then we go to the next line.
		x = visualizationPadding[3]
		y = visualizationPadding[0]
		
		lineHeight = 42 #Calculated from the trigger icon + text.
		
		def drawArrow(toElementOfWidth: int) -> None:
			"""Draw an arrow to the next element, line-wrapping if needed."""
			nonlocal x, y 
			
			if x == visualizationPadding[3] and y == visualizationPadding[0]:
				return #We have not moved, must be at start. So don't draw arrow from nothing.
			
			arrowLength = 20 #px, always px
			arrowPadding = 10
			headSize = 5
			linePadding = 20
			
			painter.save()
			painter.translate(-0.5, -0.5) #Align 1px-width lines to the *center* of pixels when integer position specified, instead of the edges of pixels. If the line is exactly on a pixel edge, it will draw half the line on one pixel and the other half on the other, at half-strength due to the AA algorithm. 😑
			path = QPainterPath() #arrow line → or the ꙅ-type
			
			
			#Initial — of the arrow.
			x += arrowPadding
			path.moveTo(x, y + lineHeight//2)
			
			x += arrowLength
			path.lineTo(x, y + lineHeight//2)
			
			#Arrow wrap around to new-line.
			if x + arrowPadding + toElementOfWidth + arrowPadding + arrowLength > visWidth - visualizationPadding[1]: #Test if element + another arrow is over the right margin.
				path.lineTo(x, y + lineHeight + linePadding//2)
				x = visualizationPadding[3] + 5 #+ indent
				path.lineTo(x, y + lineHeight + linePadding//2)
				y += lineHeight + linePadding
				path.lineTo(x, y + lineHeight//2)
				x += arrowLength #Draw the arrow head again.
				path.lineTo(x, y + lineHeight//2)
			
			path.moveTo(x - headSize - 0.5, y + lineHeight//2 - headSize) #-0.5 to make AA line up just a little better for a more consistent line thickness
			path.lineTo(x, y + lineHeight//2)
			path.lineTo(x - headSize - 0.5, y + lineHeight//2 + headSize)
			
			x += arrowPadding
			
			painter.drawPath(path)
			painter.restore()
		
		
		def drawPullup() -> None:
			"""Draw the pullup that gets sent to IO."""
			nonlocal x
			
			painter.setOpacity(strength(1))
			
			pullupAmount = 0
			if triggerId == 'trig1':
				pullupAmount += self.uiTrigger11mAPullup.isChecked()*1
				pullupAmount += self.uiTrigger120mAPullup.isChecked()*20
			if triggerId == 'trig2':
				pullupAmount += self.uiTrigger220mAPullup.isChecked()*20
				
			if pullupAmount:
				#Draw the pullup amount.
				
				text = "5V at ≤%imA" % pullupAmount
				painter.setFont(normalFont)
				textHeight = painter.fontMetrics().height()
				textWidth = painter.fontMetrics().width(text)
				
				drawArrow(textWidth)
				
				painter.drawText(QPoint(
					x,
					y+lineHeight/2 + textHeight/4
				), text)
				
				x += textWidth
		
		
		def drawIoIcon() -> None:
			"""Compute height of icon + icon label, used for line height."""
			nonlocal x
			
			painter.setOpacity(strength(triggerIsActive))
			
			icon = QImage({
				'trig1': 'assets/images/bnc-connector.png',
				'trig2': 'assets/images/green-connector.png',
				'trig3': 'assets/images/green-connector-bottom.png',
				'motion': 'assets/images/motion.png',
			}[triggerId])
			if triggerId == 'motion':
				ioText = '{0:.1f}%'.format(triggerState["level"]*100)
			else:
				ioText = '{0:.2f}V'.format(triggerState["level"])
			iconWidth = icon.width()
			
			painter.setFont(tinyFont)
			textHeight = painter.fontMetrics().height()
			lineHeight = icon.height()-3+textHeight
			textWidth = painter.fontMetrics().width(ioText)
			totalWidth = max(iconWidth, textWidth)
			
			drawArrow(totalWidth)
			
			painter.drawImage(QPoint(
				x+(totalWidth-iconWidth)/2,
				y+3, #hack, visual weight was off though geometry was ok I think
			), icon)
			
			painter.setFont(tinyFont)
			painter.drawText(QPoint(
				x+(totalWidth-textWidth)/2, 
				y+3+lineHeight,
			), ioText)
			
			x += totalWidth
		
		
		def drawInversion() -> None:
			"""Draw "invert". Flip the active state."""
			nonlocal x, triggerIsActive
			
			if {
				'trig1': self.uiTrigger1Invert,
				'trig2': self.uiTrigger2Invert,
				'trig3': self.uiTrigger3Invert,
				'motion': self.uiMotionTriggerInvert,
			}[triggerId].isChecked():
				text = "Invert Signal"
				painter.setFont(normalFont)
				textHeight = painter.fontMetrics().height()
				textWidth = painter.fontMetrics().width(text)
				
				drawArrow(textWidth)
				
				painter.drawText(QPoint(
					x,
					y + lineHeight/2 + textHeight/4
				), text)
				
				triggerIsActive = not triggerIsActive
				painter.setOpacity(strength(triggerIsActive))
				
				x += textWidth
		
		
		def drawDebounce() -> None:
			"""Draw the debounce. Draw the debounce period under it."""
			nonlocal x
			
			if {
				'trig1': self.uiTrigger1Debounce,
				'trig2': self.uiTrigger2Debounce,
				'trig3': self.uiTrigger3Debounce,
				'motion': self.uiMotionTriggerDebounce,
			}[triggerId].isChecked():
				text = "Debounce"
				painter.setFont(normalFont)
				textWidth = painter.fontMetrics().width(text)
				
				drawArrow(textWidth)
				
				painter.drawText(QPoint(
					x,
					y + lineHeight/2
				), text)
				painter.setFont(tinyFont)
				painter.drawText(QPoint(
					x,
					y + lineHeight/2 + painter.fontMetrics().height()
				), "   (10ms)   ") #cheap-o center justification
				
				x += textWidth
		
		
		def drawTriggerAction() -> None:
			nonlocal x
			
			text = {
				'trig1': self.uiTrigger1Action,
				'trig2': self.uiTrigger2Action,
				'trig3': self.uiTrigger3Action,
				'motion': self.uiMotionTriggerAction,
			}[triggerId].currentText()
			
			if text == "None":
				text = "No Action"
			
			painter.setFont(normalFont)
			textHeight = painter.fontMetrics().height()
			textWidth = painter.fontMetrics().width(text)
			
			drawArrow(textWidth)
			
			painter.drawText(QPoint(
				x,
				y + lineHeight/2 + textHeight/4
			), text)
			
			x += textWidth
		
		
		action = {
			'trig1': self.availableTrigger1Actions[self.uiTrigger1Action.currentIndex()],
			'trig2': self.availableTrigger2Actions[self.uiTrigger2Action.currentIndex()],
			'trig3': self.availableTrigger3Actions[self.uiTrigger3Action.currentIndex()],
			'motion': self.availableMotionTriggerActions[self.uiMotionTriggerAction.currentIndex()],
		}[triggerId]
		
		if action in self.outputTriggers:
			isOutputTrigger = True
			
			drawTriggerAction()
			drawPullup()
			drawInversion()
			drawIoIcon()
		else:
			drawPullup()
			drawIoIcon()
			drawInversion()
			drawDebounce() if action not in self.signalBasedTriggers else None
			drawTriggerAction()