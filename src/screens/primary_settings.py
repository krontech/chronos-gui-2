from datetime import datetime

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtGui import QPixmap
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
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
		
		self.editingSystemTime = False
		self.uiSystemTime.focusInEvent = self.sysTimeFocusIn
		self.uiSystemTime.focusOutEvent = self.sysTimeFocusOut
		self.updateDisplayedSystemTime()
		self.timeUpdateTimer = QtCore.QTimer()
		self.timeUpdateTimer.timeout.connect(self.updateDisplayedSystemTime)
		self.timeUpdateTimer.start(1000)
		
		self.uiFileSaving.clicked.connect(lambda: window.show('file_settings'))
		self.uiUserSettings.clicked.connect(lambda: window.show('user_settings'))
		self.uiAboutCamera.clicked.connect(lambda: window.show('about_camera'))
		self.uiUpdateCamera.clicked.connect(lambda: window.show('update_firmware'))
		self.uiFactoryUtilities.clicked.connect(lambda: window.show('service_screen.locked'))
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
		
	def sysTimeFocusIn(self, evt):
		self.editingSystemTime = True
		
	def sysTimeFocusOut(self, evt):
		try:
			newTime = datetime.strptime(self.uiSystemTime.text(), "%Y-%m-%d %I:%M:%S %p")
			api.set({'datetime': newTime})
			self.editingSystemTime = False
		except e: #Couldn't parse date.
			print("couldn't parse date 😭")
			pass
		
	def sysTimeBeingEdited(self):
		return self.editingSystemTime #self.uiSystemTime.hasFocus() doesn't work if invalid
		
	def updateDisplayedSystemTime(self):
		if self.sysTimeBeingEdited():
			#Prevent changes from being overwritten.
			return
		
		self.uiSystemTime.setText(
			datetime.now().strftime(
				"%Y-%m-%d %I:%M:%S %p" ) )