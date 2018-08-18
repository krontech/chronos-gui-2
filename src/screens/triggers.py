from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


settings = QtCore.QSettings('Krontech', 'back-of-camera interface')


class Triggers(QtWidgets.QDialog):
	
	#Save current screen by ID, not by index or display text because those are UI changes.
	availableTriggerIds = ['trig1', 'trig2', 'trig3', 'motion']
	
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi('src/screens/triggers.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiUnsavedChangesWarning.hide()
		
		
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
		
		# Widget behavour.
		self.uiActiveTrigger.currentIndexChanged.connect(self.changeShownTrigger)
		
		self.uiRecordMode.clicked.connect(lambda: window.show('record_mode'))
		self.uiTriggerDelay.clicked.connect(lambda: window.show('trigger_delay'))
		self.uiDone.clicked.connect(window.back)
	
	
	def changeShownTrigger(self, index):
		self.uiTriggerScreens.setCurrentIndex(index)
		settings.setValue('active trigger', self.availableTriggerIds[index])