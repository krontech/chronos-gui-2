# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtWidgets import QScroller
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api
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
			.replace('{MODEL}', f"{api.get('cameraModel')}, {api.get('cameraMemoryGB')}, {'color' if api.get('sensorRecordsColor') else 'mono'}")
			.replace('{SERIAL_NUMBER}', api.get('cameraSerial'))
			.replace('{UI_VERSION}', app_version)
			.replace('{API_VERSION}', api.get('cameraApiVersion'))
			.replace('{FPGA_VERSION}', api.get('cameraFpgaVersion'))
		)
		
		# Set scroll bar to scroll all text content. 
		self.uiScroll.setMaximum( 
			self.uiText.height() - self.uiScrollArea.height() )
		
		#Add drag-to-scroll to text content.
		self.uiScrollArea.setFocusPolicy(QtCore.Qt.NoFocus)
		QScroller.grabGesture(self.uiScrollArea.viewport(), QScroller.LeftMouseButtonGesture) #DDR 2019-01-15: Defaults to TouchGesture - which should work, according to WA_AcceptTouchEvents, but doesn't.
		scroller = QScroller.scroller(self.uiScrollArea.viewport())
		properties = scroller.scrollerProperties()
		properties.setScrollMetric(properties.AxisLockThreshold, 0.0)
		properties.setScrollMetric(properties.MousePressEventDelay, 0.0)
		properties.setScrollMetric(properties.DragStartDistance, 0.0) #default: 0.005 - tweaked for "feel", the platform defaults are overly dramatic.
		properties.setScrollMetric(properties.OvershootDragDistanceFactor, 0.3) #default: 1
		properties.setScrollMetric(properties.OvershootScrollDistanceFactor, 0.3) #default: 1
		properties.setScrollMetric(properties.OvershootScrollTime, 0.5) #default: 0.7
		scroller.setScrollerProperties(properties)
		
		# Button binding.
		self.uiScroll.valueChanged.connect(self.scrollPane)
		self.uiScrollArea.verticalScrollBar().valueChanged.connect(self.scrollKnob)
		
		self.uiDone.clicked.connect(window.back)
	
	@api.silenceCallbacks('uiScrollArea')
	def scrollPane(self, pos):
		"""Update the text position when the slider position changes."""
		self.uiScrollArea.verticalScrollBar().setValue(pos)
	
	@api.silenceCallbacks('uiScroll')
	def scrollKnob(self, pos):
		"""Update the slider position when the text position changes."""
		self.uiScroll.setValue(pos)