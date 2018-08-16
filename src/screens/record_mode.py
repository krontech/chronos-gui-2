from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


settings = QtCore.QSettings('Krontech', 'back-of-camera interface')


class RecordMode(QtWidgets.QDialog):
	
	#Save current screen by ID, not by index or display text because those are UI changes.
	availableRecordModeIds = ['regular', 'segmented', 'runAndGun']
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi('src/screens/record_mode.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		
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
		self.uiRecordModePanes.setCurrentIndex(index)
		settings.setValue('active record mode', self.availableRecordModeIds[index])