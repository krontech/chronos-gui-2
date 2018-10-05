from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api as api
from stats import app_version


class AboutCamera(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/about_camera.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		#Substitute constants into header bit.
		self.uiText.setText(
			self.uiText.text()
			.replace('{MODEL}', f"{api.get('cameraModel')}, {api.get('cameraMemoryGB')}, {'colour' if api.get('sensorRecordsColour') else 'mono'}")
			.replace('{SERIAL_NUMBER}', api.get('cameraSerial'))
			.replace('{UI_VERSION}', app_version)
			.replace('{API_VERSION}', api.get('cameraApiVersion'))
			.replace('{FPGA_VERSION}', api.get('cameraFpgaVersion'))
		)
		
		# Set scroll bar to scroll all text content. 
		self.uiScroll.setMaximum( 
			self.uiText.height() - self.uiScrollArea.height() )
		
		self.uiScrollArea.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		self.uiScrollArea.setFocusPolicy(QtCore.Qt.NoFocus)
		
		# Button binding.
		self.uiScroll.valueChanged.connect(self.scrollPane)
		
		self.uiDone.clicked.connect(window.back)
		
	def scrollPane(self, pos):
		"""Update the text position when scrollbar changes."""
		
		self.uiScrollArea.verticalScrollBar().setValue(pos)