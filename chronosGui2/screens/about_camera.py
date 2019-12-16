# -*- coding: future_fstrings -*-
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QScroller
# from PyQt5.QtCore import pyqtSlot

import chronosGui2.api as api
import chronosGui2.settings as settings
from chronosGui2.debugger import *; dbg
from theme import theme

# Import the generated UI form and app version.
from chronosGui2.generated import __version__ as appVersion
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_AboutCamera
else:
	from chronosGui2.generated.chronos import Ui_AboutCamera

class AboutCamera(QtWidgets.QDialog, Ui_AboutCamera):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# API init.
		self.control = api.control()

		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		#Substitute constants into header bit.
		self.control.get(['cameraModel', 'cameraMemoryGB', 'sensorColorPattern', 'cameraSerial', 'cameraApiVersion', 'cameraFpgaVersion']).then(
			lambda values:
				self.uiText.setText(
					self.uiText.text()
					.replace('{MODEL}', f"{values['cameraModel']}, {values['cameraMemoryGB']}, {'mono' if values['sensorColorPattern'] == 'mono' else 'color'}")
					.replace('{SERIAL_NUMBER}', values['cameraSerial'])
					.replace('{UI_VERSION}', appVersion)
					.replace('{API_VERSION}', values['cameraApiVersion'])
					.replace('{FPGA_VERSION}', values['cameraFpgaVersion'])
				)
		)
		settings.observe('theme', 'dark', lambda name: (
			self.uiScrollArea.setStyleSheet(f"""
				color: {theme(name).text};
				background: {theme(name).base};
				border: 1px solid {theme(name).border};
			"""),
			self.uiText.setStyleSheet(f"""
				border: none;
				padding: 5px;
			""")
		))
		
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
	
	def scrollPane(self, pos):
		"""Update the text position when the slider position changes."""
		self.uiScrollArea.verticalScrollBar().setValue(pos)
	
	def scrollKnob(self, pos):
		"""Update the slider position when the text position changes."""
		self.uiScroll.setValue(pos)
