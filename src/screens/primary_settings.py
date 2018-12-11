from datetime import datetime

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks
import settings


class PrimarySettings(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/primary_settings.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		
		#Side and rotated are not quite correct, as askBeforeDiscarding is, but they are correct enough for now. Having the final result come from two values confused things a bit.
		self.uiInterfaceSide.setCurrentIndex(
			int(settings.value('interface handedness') == 'left'))
		self.uiInterfaceSide.currentIndexChanged.connect(lambda index:
			settings.setValue('interface handedness', 'left' if index else 'right') )
		settings.observe('interface handedness', self.updateInterfaceSide)
		
		self.uiInterfaceRotated.setCurrentIndex(
			int(settings.value('interface rotation') == '180'))
		self.uiInterfaceRotated.currentIndexChanged.connect(lambda index:
			settings.setValue('interface rotation', '180' if index else '0') )
		settings.observe('interface rotation', self.updateInterfaceSide)
		
		#Note the operations attached here:
		#	- We must observe a silenced callback to update the state. This prevents an infinite loop.
		#	- We update the state from a callback attached to the widget.
		settings.observe('ask before discarding', self.updateAskBeforeDiscarding)
		self.uiAskBeforeDiscarding.currentIndexChanged.connect(lambda index:
			settings.setValue('ask before discarding',
				["always", "if not reviewed", "never"][index] ) )
		
		
		api.observe('datetime', self.stopEditingDate) #When the date is changed, always display the update even if an edit is in progress. Someone probably set the date some other way instead of this, or this was being edited in error.
		self.uiSystemTime.focusInEvent = self.sysTimeFocusIn
		self.uiSystemTime.focusOutEvent = self.sysTimeFocusOut
		self.updateDisplayedSystemTime()
		self.timeUpdateTimer = QtCore.QTimer()
		self.timeUpdateTimer.timeout.connect(self.updateDisplayedSystemTime)
		self.timeUpdateTimer.start(1000)
		
		self.uiAboutCamera.clicked.connect(lambda: window.show('about_camera'))
		self.uiRemoteAccess.clicked.connect(lambda: window.show('remote_access'))
		self.uiFactoryUtilities.clicked.connect(lambda: window.show('service_screen.locked'))
		self.uiFileSaving.clicked.connect(lambda: window.show('file_settings'))
		self.uiStorage.clicked.connect(lambda: window.show('storage'))
		self.uiUpdateCamera.clicked.connect(lambda: window.show('update_firmware'))
		self.uiUserSettings.clicked.connect(lambda: window.show('user_settings'))
		self.uiDone.clicked.connect(window.back)
		
	
	def updateInterfaceSide(self, *_):
		self.uiLayoutPreview.setPixmap(QPixmap(
			f"assets/images/interface-{'left' if self.uiInterfaceSide.currentIndex() else 'right'}-{'down' if self.uiInterfaceRotated.currentIndex() else 'up'}.svg"
		))
		
		#How to rotate stuff:
		# rotation = QTransform() #from QtGui
		# rotation.rotate(180*self.uiInterfaceRotated.currentIndex())
		# self.uiLayoutPreview.setPixmap(QPixmap(
		# 	"assets/images/left-handed-interface.svg"
		# 	if self.uiInterfaceSide.currentIndex() else
		# 	"assets/images/right-handed-interface.svg"
		# ).transformed(rotation))
	
	@silenceCallbacks('uiAskBeforeDiscarding')
	def updateAskBeforeDiscarding(self, answer: str="if not reviewed"):
		self.uiAskBeforeDiscarding.setCurrentIndex(
			["always", "if not reviewed", "never"].index(answer))
	
	
	@pyqtSlot(str, name="stopEditingDate")
	@silenceCallbacks()
	def stopEditingDate(self, date: str=''):
		self.editingSystemTime = False
	
	def sysTimeFocusIn(self, evt):
		self.editingSystemTime = True
		
	def sysTimeFocusOut(self, evt):
		try:
			newTime = datetime.strptime(self.uiSystemTime.text(), "%Y-%m-%d %I:%M:%S %p")
		except ValueError: #Probably means we couldn't parse the date.
			return self.uiSystemClockFeedback.showError("Date not formatted correctly; format is YYYY-MM-DD HH:MM:SS AM or PM.")
		
		api.set({'datetime': newTime.isoformat()}) #This causes stopEditingDate to be called, when datetime is updated.
		self.uiSystemClockFeedback.showMessage("System date updated.")
		
	def sysTimeBeingEdited(self):
		return self.editingSystemTime #self.uiSystemTime.hasFocus() doesn't work if invalid
		
	def updateDisplayedSystemTime(self):
		if self.sysTimeBeingEdited():
			#Prevent changes from being overwritten.
			return
		
		self.uiSystemTime.setText(
			datetime.now().strftime(
				"%Y-%m-%d %I:%M:%S %p" ) ) #TODO DDR 2018-09-24: Convert this into a series of plain number inputs.