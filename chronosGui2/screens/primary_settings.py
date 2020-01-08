# -*- coding: future_fstrings -*-

import os
from datetime import datetime

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QStandardItemModel

import chronosGui2.settings as settings
import chronosGui2.api as api
from chronosGui2.debugger import *; dbg

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_PrimarySettings
else:
	from chronosGui2.generated.chronos import Ui_PrimarySettings

class PrimarySettings(QtWidgets.QDialog, Ui_PrimarySettings):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.window_ = window
		
		#Side and rotated are not quite correct, as askBeforeDiscarding is, but they are correct enough for now. Having the final result come from two values confused things a bit.
		self.uiInterfaceSide.setCurrentIndex(
			int(settings.value('interface handedness', None) == 'left'))
		self.uiInterfaceSide.currentIndexChanged.connect(lambda index:
			settings.setValue('interface handedness', 'left' if index else 'right') )
		settings.observe('interface handedness', None, self.updateInterfaceSide)
		
		self.uiInterfaceRotated.setCurrentIndex(
			int(settings.value('interface rotation', None) == '180'))
		self.uiInterfaceRotated.currentIndexChanged.connect(lambda index:
			settings.setValue('interface rotation', '180' if index else '0') )
		settings.observe('interface rotation', None, self.updateInterfaceSide)
		
		settings.observe('theme', 'dark', self.updateInterfaceSide)
		
		#Note the operations attached here:
		#	- We must observe a silenced callback to update the state. This prevents an infinite loop.
		#	- We update the state from a callback attached to the widget.
		settings.observe('ask before discarding', 'if not reviewed', self.updateAskBeforeDiscarding)
		self.uiAskBeforeDiscarding.currentIndexChanged.connect(lambda index:
			settings.setValue('ask before discarding',
				["always", "if not reviewed", "never"][index] ) )
		
		
		api.observe('dateTime', self.stopEditingDate) #When the date is changed, always display the update even if an edit is in progress. Someone probably set the date some other way instead of this, or this was being edited in error.
		self.uiSystemTime.focusInEvent = self.sysTimeFocusIn
		self.uiSystemTime.editingFinished.connect(self.sysTimeFocusOut)
		self._timeUpdateTimer = QtCore.QTimer()
		self._timeUpdateTimer.timeout.connect(self.updateDisplayedSystemTime)
		
		
		self.uiDone.clicked.connect(window.back)
	
	def onShow(self):
		self.updateDisplayedSystemTime()
		self._timeUpdateTimer.start(1000)
	
	def onHide(self):
		self._timeUpdateTimer.stop()
	
	
	def updateInterfaceSide(self, *_):
		self.uiLayoutPreview.setPixmap(QPixmap(
			dump(f"assets/images/interface-{settings.value('theme', 'dark')}-{'left' if self.uiInterfaceSide.currentIndex() else 'right'}-{'down' if self.uiInterfaceRotated.currentIndex() else 'up'}.png")
		))
		
		#How to rotate stuff:
		# rotation = QTransform() #from QtGui
		# rotation.rotate(180*self.uiInterfaceRotated.currentIndex())
		# self.uiLayoutPreview.setPixmap(QPixmap(
		# 	"assets/images/left-handed-interface.svg"
		# 	if self.uiInterfaceSide.currentIndex() else
		# 	"assets/images/right-handed-interface.svg"
		# ).transformed(rotation))
	
	def updateAskBeforeDiscarding(self, answer):
		self.uiAskBeforeDiscarding.setCurrentIndex(
			["always", "if not reviewed", "never"].index(answer))
	
	
	@pyqtSlot(str, name="stopEditingDate")
	def stopEditingDate(self, date: str=''):
		self.editingSystemTime = False
	
	def sysTimeFocusIn(self, *_):
		self.editingSystemTime = True
		
	def sysTimeFocusOut(self, *_):
		#try:
		#	newTime = datetime.strptime(self.uiSystemTime.text(), "%Y-%m-%d %I:%M:%S %p")
		#except ValueError: #Probably means we couldn't parse the date.
		#	return self.uiSystemClockFeedback.showError("Date not formatted correctly; format is YYYY-MM-DD HH:MM:SS AM or PM.")
		
		(api.set({'dateTime': self.uiSystemTime.text()}) #newTime.isoformat()})
			.then(lambda status: 
				self.uiSystemClockFeedback.showMessage(
					"System date updated." ) )
			.catch(lambda error:
				self.uiSystemClockFeedback.showError(
					error ) )
		)
		
		self.stopEditingDate()
		
	def sysTimeBeingEdited(self):
		return self.editingSystemTime #self.uiSystemTime.hasFocus() doesn't work if invalid
		
	def updateDisplayedSystemTime(self):
		if self.sysTimeBeingEdited():
			#Prevent changes from being overwritten.
			return
		
		#TODO DDR 2018-09-24: Convert this into a series of plain number inputs.
		api.get('dateTime').then(self.uiSystemTime.setText)
