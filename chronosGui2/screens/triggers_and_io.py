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

from functools import partial
from collections import defaultdict

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QItemSelection, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel

import chronosGui2.settings as settings
import chronosGui2.api as api
from chronosGui2.debugger import *; dbg

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_TriggersAndIo
else:
	from chronosGui2.generated.chronos import Ui_TriggersAndIo

tr = partial(QtCore.QCoreApplication.translate, "Triggers")

#Keep unsaved changes when something else changes them?
KEEP_CHANGES = True
DISCARD_CHANGES = False
updateMode = KEEP_CHANGES

#Verify this against cam-json get - <<< '["ioDetailedStatus"]'?
actionData = [
	{ 'id': 'start',       'tags': {'action', 'video', 'edge'},         'name': tr("Start Recording"),       'shortName':tr("Start Rec.")     },
	{ 'id': 'stop',        'tags': {'action', 'video', 'edge'},         'name': tr("Stop Recording"),        'shortName':tr("Stop Rec.")      },
	{ 'id': 'io1',         'tags': {'action', 'trigger', 'level'},      'name': tr("Output to TRIG1⇄"),      'shortName':tr("TRIG1⇄")         },
	{ 'id': 'io2',         'tags': {'action', 'trigger', 'level'},      'name': tr("Output to TRG2⇄"),       'shortName':tr("TRG2⇄")          },
	{ 'id': 'delay',       'tags': {'time', 'level'},                   'name': tr("Delay the Signal"),      'shortName':tr("Delay")          },
	{ 'id': 'shutter',     'tags': {'action', 'shutter', 'edge'},       'name': tr("Open Shutter"),          'shortName':tr("Open Shutter")   },
	{ 'id': 'gate',        'tags': {'action', 'shutter', 'level'},      'name': tr("Shutter Gating"),        'shortName':tr("Shutter Gating") },
	{ 'id': 'combOr1',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block OR #1"), 'shortName':tr("Logic Block")    },
	{ 'id': 'combOr2',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block OR #2"), 'shortName':tr("Logic Block")    },
	{ 'id': 'combOr3',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block OR #3"), 'shortName':tr("Logic Block")    },
	{ 'id': 'combAnd',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block AND"),   'shortName':tr("Logic Block")      },
	{ 'id': 'combXOr',     'tags': {'logic', 'combinatorial', 'level'}, 'name': tr("Set Logic Block XOR"),   'shortName':tr("Logic Block")      },
	{ 'id': 'toggleClear', 'tags': {'logic', 'toggle', 'edge'},         'name': tr("Turn Flipflop Off"),     'shortName':tr("Flipflop Off")   },
	{ 'id': 'toggleSet',   'tags': {'logic', 'toggle', 'edge'},         'name': tr("Turn Flipflop On"),      'shortName':tr("Flipflop On")    },
	{ 'id': 'toggleFlip',  'tags': {'logic', 'toggle', 'edge'},         'name': tr("Toggle the Flipflop"),   'shortName':tr("Flipflop")       },
]
triggerData = [
	{ 'id': 'none',        'tags': {'constant'},                        'name': { 'whenLevelTriggered': tr("Never"),                          'whenEdgeTriggered': tr("Never")                         }, 'shortName': tr("Never")            },             
	{ 'id': 'virtual',     'tags': {'emulated', 'software', 'special'}, 'name': { 'whenLevelTriggered': tr("While Record Button Held"),       'whenEdgeTriggered': tr("When Record Button Pressed")    }, 'shortName': tr("Rec. Button")      },               
	{ 'id': 'io1',         'tags': {'io'},                              'name': { 'whenLevelTriggered': tr("While TRIG1⇄ Input"),             'whenEdgeTriggered': tr("On TRIG1⇄ Input")               }, 'shortName': tr("TRIG1⇄")           },                           
	{ 'id': 'io2',         'tags': {'io'},                              'name': { 'whenLevelTriggered': tr("While TRIG2⇄ Input"),             'whenEdgeTriggered': tr("On TRIG2⇄ Input")               }, 'shortName': tr("TRIG2⇄")           },                           
	{ 'id': 'io3',         'tags': {'io'},                              'name': { 'whenLevelTriggered': tr("While TRIG3± Input"),             'whenEdgeTriggered': tr("On TRIG3± Input")               }, 'shortName': tr("TRIG3±")           },                           
	{ 'id': 'audio',       'tags': {'disabled'},                        'name': { 'whenLevelTriggered': tr("While Audio Detected"),           'whenEdgeTriggered': tr("When Audio Detected")           }, 'shortName': tr("Audio")            },                                         
	{ 'id': 'motion',      'tags': {'disabled'},                        'name': { 'whenLevelTriggered': tr("While Motion Detected"),          'whenEdgeTriggered': tr("When Motion Detected")          }, 'shortName': tr("Motion")           },                                           
	{ 'id': 'delay',       'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Delayed Signal Arrives"),   'whenEdgeTriggered': tr("When Delayed Signal Arrives")   }, 'shortName': tr("Delay")            },                                                           
	{ 'id': 'comb',        'tags': {'logic', 'combinatorial'},          'name': { 'whenLevelTriggered': tr("While Logic Block Is True"),      'whenEdgeTriggered': tr("When Logic Block Becomes True") }, 'shortName': tr("Logic Block")      },                                         
	{ 'id': 'toggle',      'tags': {'logic', 'toggle'},                 'name': { 'whenLevelTriggered': tr("While Flipflop On"),              'whenEdgeTriggered': tr("When Flipflop Turns On")        }, 'shortName': tr("Flipflop")         },                                     
	{ 'id': 'shutter',     'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Shutter Open"),             'whenEdgeTriggered': tr("When Shutter Opens")            }, 'shortName': tr("Shutter Opens")    },                                       
	{ 'id': 'recording',   'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Recording"),                'whenEdgeTriggered': tr("When Recording Starts")         }, 'shortName': tr("Recording Starts") },                                 
	{ 'id': 'dispFrame',   'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When Frame Recorded"),            'whenEdgeTriggered': tr("When Frame Recorded")           }, 'shortName': tr("Frame Recorded")   },                                     
	{ 'id': 'startRec',    'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When Recording Starts"),          'whenEdgeTriggered': tr("When Recording Starts")         }, 'shortName': tr("Recording Starts") },                                       
	{ 'id': 'endRec',      'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When Recording Ends"),            'whenEdgeTriggered': tr("When Recording Ends")           }, 'shortName': tr("Recording Ends")   },                                   
	{ 'id': 'nextSeg',     'tags': {'pulse'},                           'name': { 'whenLevelTriggered': tr("When New Segment"),               'whenEdgeTriggered': tr("When New Segment")              }, 'shortName': tr("New Segment")      },                               
	{ 'id': 'timingIo',    'tags': {},                                  'name': { 'whenLevelTriggered': tr("While Timing Signal"),            'whenEdgeTriggered': tr("On Timing Signal")              }, 'shortName': tr("Timing Signal")    },                             
	{ 'id': 'alwaysHigh',  'tags': {'constant'},                        'name': { 'whenLevelTriggered': tr("Always"),                         'whenEdgeTriggered': tr("Once")                          }, 'shortName': tr("Always")           },               
]

actionTriggers = defaultdict(lambda: None, { #Map actions to the trigger triggering it.
	'io1': 'io1',
	'io2': 'io2',
	'delay': 'delay',
	'shutter': 'shutter',
	'gate': 'shutter',
	'combOr1': 'comb',
	'combOr2': 'comb',
	'combOr3': 'comb',
	'combAnd': 'comb',
	'combXOr': 'comb',
	'toggleClear': 'toggle',
	'toggleSet': 'toggle',
	'toggleFlip': 'toggle',
})


def default(*args):
	for arg in args:
		if arg is not None:
			return arg
	return args[-1]



class TriggersAndIO(QtWidgets.QDialog, Ui_TriggersAndIo):
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
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# State init, screen loads in superposition.
		self.markStateClean()
		#Only needed when trigger for action is set to Never, because the index changed event will never fire then and we'll be stuck with whatever index was set in the .ui file. Ideally, this would not be set in the .ui file in the first place, but realistically since it's set when we change "panels" with the little arrows at the top of the pane we're not gonna remember to clear it every time in the property editor and it'll just be a stupid recurring bug. So fix it here.
		self.uiIndividualTriggerConfigurationPanes.setCurrentIndex(0) 
		
		self.load(actions=actionData, triggers=triggerData)
		
		self.oldIOMapping = defaultdict(lambda: defaultdict(lambda: None)) #Set part and parcel to whatever the most recent mapping is.
		self.newIOMapping = defaultdict(lambda: defaultdict(lambda: None)) #Set piece-by-piece to the new mapping.
		api.observe('ioMapping', self.onNewIOMapping)
		
		
		self.uiActionList.selectionModel().selectionChanged.connect(
			self.onActionChanged)
		self.uiTriggerList.currentIndexChanged.connect(lambda index:
			self.uiIndividualTriggerConfigurationPanes.setCurrentIndex(
				self.uiTriggerList.itemData(index) ) )
		self.uiActionList.selectionModel().setCurrentIndex(
			self.uiActionList.model().index(0,0),
			QItemSelectionModel.ClearAndSelect )
		self.uiActionList.selectionModel().selectionChanged.connect(
			self.uiPreview.update )
		
		self.uiTriggerList.currentIndexChanged.connect(self.onTriggerChanged)
		self.uiTriggerList.currentIndexChanged.connect(self.uiPreview.update)
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
		
		#TODO: Add little visualisation showing what connects and what is connected to the current action.
		self.uiPreview.paintEvent = self.paintPreview
	
	def markStateClean(self, *_):
		self.uiUnsavedChangesWarning.hide()
		self.uiSave.hide()
		self.uiDone.show()
		self.uiCancel.hide()
		
	def markStateDirty(self, *_):
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
					Qt.DisplayRole: triggers[triggerIndex]['name']['whenEdgeTriggered'],
					Qt.UserRole: triggerIndex,
				})
	
	
	def resetChanges(self, *_):
		self.newIOMapping = defaultdict(lambda: defaultdict(lambda: None))
		self.onActionChanged(self.uiActionList.selectionModel().selection())
		
		ioMapping = api.apiValues.get('ioMapping')
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
		ioMapping = api.apiValues.get('ioMapping')
		
		existingVirtuals = settings.value('virtually triggered actions', {})
		newVirtuals = {
			trigger
			for trigger, configuration in self.newIOMapping.items()
			if 'virtual' in configuration.values()
		}
		
		virtuals = { #Merge old and new virtuals configurations, filtering out old virtuals which are no longer and adding new virtuals.
			action: { #Merge the keys of the old and new virtual, since someone could have updated only, say, invert.
				key: default(
					self.newIOMapping.get(action, {}).get(key), #Find "most recent" value, defaulting to false if it was never set.
					existingVirtuals.get(action, {}).get(key),
					False )
				for key in self.newIOMapping.get(action, {}).keys() | existingVirtuals.get(action, {}).keys()
			}
			for action in existingVirtuals.keys() | newVirtuals #Consider only actions which are or were virtuals. Now, we need to filter out items which aren't verticals any more, and merge those which are.
			if self.newIOMapping.get(action, {}).get('source') in (None, 'virtual') #Filter out newly non-virtual actions, allowing unchanged and newly-virtual actions.
		}
		settings.setValue('virtually triggered actions', virtuals)
		pp({
			'newIOMapping': self.newIOMapping,
			'existingVirtuals': existingVirtuals, 
			'newVirtuals': newVirtuals, 
			'virtuals': virtuals,
		})
		
		api.set('ioMapping', dump('sending IO mapping', { #Send along the update delta. Strictly speaking, we could send the whole thing and not a delta, but it seems more correct to only send what we want to change. data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAjCAMAAAApB0NrAAAAdVBMVEUAAAAAFBwCJTYbKjQjOUwoPlI/QT5GTFRDVmVQY3N4XGhgZGbUPobePYXgQY2BZnedZ4GBeH7EYqCXdYjbX5yigJOIjI+NkZTgfai5jZ2gnaHkire6m6fknsPxm8CtsrToqczrr8S9wsTwttHztszzuNPe4N2lYYACAAAAAXRSTlMAQObYZgAAAaBJREFUOMt9kwFTgzAMhVGn4ibMuqql40WFxP//E01TNgpu5o47Lnx9SV9CVS3Dp6iuRVPEZeK1RJrWN43/V+WKWinjg2/zyzUZDxGGvyA0MwkhypC/zHgiFgiqNeObkiGAyXIFo00W3QBdB5h0wWieMtVi7GJ0255XjCcRIR8ABMHh/WOIyEy1ZIRF0Onjhrr+jFbreWZaZGDvemX7n7h7ykxRrDkyCXo3DIOa0+/cw+YddnnvX086XjvBNsbaKfPtNjf3W3xpeuEOhPpt/Nnd98yEt/1LMnE1CO0azkX3eNCqzNBL0Hr31Dp+c5uHu4OoxToMnWr1FwpdrG83qZY5gYkBUMzUd67ew0RERhCMSHgx94A+pcxPQqoG40umBfOYETtPoHwCxf4cNat7ocshpgAUTDY1cD5MYypmTU2qCVHtYEs6B86t2cXUZBYOQRaBUWYPIKPtT26QTufJoMkd8PS1bNNq8Oxkdk3s69HTCdKBnZ0BzU1Q285Ci2mdC6TFn2+3nOpUjo/JyCtMZZNh2+HARUMrSP21/zWMf3V+AVFTVrq9UKSZAAAAAElFTkSuQmCC
			action: 
				{
					key: default(newConfig[key], value)
					for key, value in ioMapping[action].items()
				}
				if action not in virtuals else
				{ 
					'source': 'none', #Disable the input of any virtual element. It is set to "always" to implement the virtual trigger firing.
					'invert': default(newConfig['invert'], ioMapping[action]['invert']),
					'debounce': default(newConfig['debounce'], ioMapping[action]['debounce']),
				}
			for action, newConfig in self.newIOMapping.items()
			if [value for value in newConfig.values() if value is not None]
		})).then(self.saveChanges2)
	def saveChanges2(self, *_):
		self.newIOMapping = defaultdict(lambda: defaultdict(lambda: None))
		self.markStateClean()
	
	
	def onNewIOMapping(self, ioMapping: dict):
		"""Update the IO display with new values, overriding any pending changes."""
		selectedAction = actionData[self.uiActionList.selectionModel().currentIndex().data(Qt.UserRole) or 0]['id']
		virtuals = settings.value('virtually triggered actions', {}) #Different from soft trigger, that's a hardware-based interrupt thing. The virtual trigger is a gui2 hallucination.
		
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
			
			if action in virtuals:
				virtual = virtuals[action]
				
				self.uiInvertCondition.blockSignals(True)
				self.uiInvertCondition.setChecked(default(
					delta['invert'], virtual.get('invert'), False ))
				self.uiInvertCondition.blockSignals(False)
				
				self.uiDebounce.blockSignals(True)
				self.uiDebounce.setChecked(default(
					delta['debounce'], virtual.get('debounce'), False ))
				self.uiDebounce.blockSignals(False)
				
				continue
			
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
		config = api.apiValues.get('ioMapping')[action['id']]
		newConfig = self.newIOMapping[action['id']]
		virtuals = settings.value('virtually triggered actions', {})
		
		if action['id'] in virtuals:
			source = newConfig['source'] or 'virtual'
			virtual = source == 'virtual'
		else:
			source = newConfig['source'] or config['source']
			virtual = None
		
		dataIndex = [trigger['id'] for trigger in triggerData].index(source)
		
		listIndex = self.uiTriggerList.findData(dataIndex)
		assert listIndex is not -1, f"Could not find index for {config['source']} ({dataIndex}) in uiTriggerList."
		
		try: #Fix for state getting marked dirty when we view a different action.
			self.uiTriggerList.currentIndexChanged.disconnect(self.markStateDirty)
			self.uiTriggerList.setCurrentIndex(listIndex)
			self.uiTriggerList.currentIndexChanged.connect(self.markStateDirty)
		except TypeError: #'method' object is not connected, whatever, just set index then.
			self.uiTriggerList.setCurrentIndex(listIndex)
		
		self.uiInvertCondition.blockSignals(True) #We can block these signals because nothing else depends on them. A few things depend on the Trigger for Action combobox, so it is just a little smarter about it's updates to deal with this changing.
		self.uiInvertCondition.setChecked(bool(default(
			newConfig['invert'], 
			(virtuals[action['id']].get('invert') or False) if virtual else None, #.get returns False or None, we always want False so default stops here if this is a virtual trigger.
			config['invert'],
		)))
		self.uiInvertCondition.blockSignals(False)
		
		self.uiDebounce.blockSignals(True)
		self.uiDebounce.setChecked(bool(default(
			newConfig['debounce'], 
			(virtuals[action['id']].get('debounce') or False) if virtual else None,
			config['debounce'],
		)))
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
		virtuals = settings.value('virtually triggered actions', {})
		oldSource = api.apiValues.get('ioMapping')[activeAction['id']]['source']
		if oldSource == newSource and activeAction['id'] not in virtuals: #If this was a virtual item, don't delete it if it's the same as what's corporeal. (Virtual defaults to "none", so if we switch from "virtual" to "none" we're actually switching from "none" to "none" which gets optimized out, which means we don't actually switch.
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
		pp(api.apiValues.get('ioMapping'))
		print()
		print('pending:')
		pp(self.newIOMapping)
		print()
		print('virtual:')
		pp(settings.value('virtually triggered actions', {}))
		print()
		dbg()
	
	
	def paintPreview(self, evt):
		"""Plot a little diagram showing what is happening.
			
			┌─Preview─────────────────────────────────────────┐
			│                                ┌─ Trig. 1       │
			│   Comb. Block ─── Delay Block ─┼─ Trig. 2       │
			│                                └─ Comb. Block   │
			└─────────────────────────────────────────────────┘
			    ^ trigger ^     ^ action ^    ^ consequence ^   """
		
		padding = (5,5) #Space around arrows.
		lineLength = 15 #Arrow line length
		lineOffset = 3 #Vertical offset, align arrows with text midline.
		
		ioMapping = api.apiValues.get('ioMapping')
		currentActionIndex = self.uiActionList.selectionModel().currentIndex().data(Qt.UserRole) or 0
		
		trigger = triggerData[self.uiTriggerList.currentData() or 0]['shortName']
		action = actionData[currentActionIndex]['shortName']
		consequences = [
			action['shortName']
			for action in actionData
			if default(
				self.newIOMapping[action['id']]['source'], 
				ioMapping[action['id']]['source'],
			) == actionTriggers[actionData[currentActionIndex]['id']]
		]
		
		
		
		QPainter = QtGui.QPainter
		QPen = QtGui.QPen
		QFont = QtGui.QFont
		QPainterPath = QtGui.QPainterPath
		
		p = QPainter(self.uiPreview)
		p.setRenderHint(QPainter.Antialiasing, False)
		p.setRenderHint(QPainter.TextAntialiasing, True)
		pen = QPen()
		p.setPen(pen)
		font = QFont("DejaVu Sans", 11, weight=QtGui.QFont.Thin)
		p.setFont(font)
		fontMetrics = QtGui.QFontMetrics(font)
		path = QPainterPath()
		
		lineHeight = fontMetrics.height()
		totalHeight = (lineHeight + padding[1])*(len(consequences) or 1) - padding[1]
		
		def drawArrowFrom(x,y, length):
			headSize = 4
			headX = x+length
			y = y + lineOffset
			path.moveTo(x, y)
			path.lineTo(headX, y)
			path.moveTo(headX - headSize, y-headSize)
			path.lineTo(headX, y)
			path.lineTo(headX - headSize, y+headSize)
		
		#Track right edge as we move over the canvas.
		x = 0
		
		#Draw Trigger.
		p.drawText(x, totalHeight/2 + lineHeight/2, trigger)
		x += fontMetrics.width(trigger) + padding[0]
		
		#Draw line to action.
		drawArrowFrom(x, totalHeight/2, lineLength)
		x += lineLength + padding[0]
		
		#Draw action.
		p.drawText(x, totalHeight/2 + lineHeight/2, action)
		x += fontMetrics.width(action) + padding[0]
		
		#Draw tree of consequences.
		if len(consequences) > 1:
			#Trunk
			path.moveTo(x, totalHeight/2 + lineOffset)
			x += lineLength*0.75
			path.lineTo(x, totalHeight/2 + lineOffset)
		
			#Branch
			path.moveTo(x, lineHeight/2 + lineOffset)
			path.lineTo(x, totalHeight - lineHeight/2 + lineOffset)
		
		if len(consequences) > 0:
			#Leaves
			y = lineHeight/2
			for consequence in consequences:
				drawArrowFrom(x, y, lineLength*0.85)
				p.drawText(x + lineLength*0.85 + padding[0], y + lineHeight/2, consequence)
				y += lineHeight + padding[1]
		
		p.drawPath(path)
