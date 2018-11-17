from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QByteArray
from PyQt5.QtGui import QImage, QTransform, QPainter

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


class PlayAndSave(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/play_and_save.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiBatteryReadout.anchorPoint = self.uiBatteryReadout.rect()
		self.uiBatteryReadout.formatString = self.uiBatteryReadout.text()
		self.updateBatteryTimer = QtCore.QTimer()
		self.updateBatteryTimer.timeout.connect(self.updateBattery)
		self.updateBatteryTimer.setInterval(2000) #ms
		
		self.uiSeekSlider.setStyleSheet(
			self.uiSeekSlider.styleSheet() + f"""
				/* ----- Play And Save Screen Styling ----- */
				
				Slider::handle:horizontal {{
					image: url({"../../" if self.uiSeekSlider.showHitRects else ""}assets/images/handle-bars-156x61+40.svg); /* File name fields: width x height + horizontal padding. */
					margin: -200px -40px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
				}}
				
				Slider::groove {{
					border: none;
				}}
			""")
		self.uiSeekSlider.valueChanged.connect(print)
		
		self.motionHeatmap = QImage() #Updated by updateMotionHeatmap, used by self.paintMotionHeatmap.
		self.uiTimelineVisualization.paintEvent = self.paintMotionHeatmap
		
		# Button binding.
		self.uiSavedFileSettings.clicked.connect(lambda: window.show('file_settings'))
		self.uiDone.clicked.connect(window.back)
		
		
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		self.updateBattery()
		self.updateBatteryTimer.start()
		self.updateMotionHeatmap(api.control('waterfallMotionMap', 'placeholder', 0))
		#Set camera to video playback mode here. This will be janky as heeeeeeeck.
		
	def onHide(self):
		self.updateBatteryTimer.stop()
	
	def updateBattery(self):
		self.uiBatteryReadout.setText(
			self.uiBatteryReadout.formatString.format(
				api.get('batteryCharge')*100 ) )
	
	def updateMotionHeatmap(self, motionData: {"startFrame": int, "endFrame": int, "heatmap": QByteArray}) -> None:
		"""Repaint the motion heatmap when we enter this screen.
			
			We never record while on the playback screen, so we don't
			have to live-update here. This is partially due to the
			fact that the camera is modal around this, it can either
			record xor playback."""
		
		heatmapHeight = 16
		
		motionData = QByteArray.fromRawData(motionData["heatmap"]) # n×16 heatmap
		assert len(motionData) % heatmapHeight == 0, f"Incompatible heatmap size {len(motionData)}; must be a multiple of {heatmapHeight}."
		
		self.motionHeatmap = (
			QImage( #Rotated 90°, since the data is packed line-by-line. We'll draw it counter-rotated.
				heatmapHeight,
				len(motionData)//heatmapHeight,
				QImage.Format_Grayscale8)
			.transformed(QTransform().rotate(-90))
			.scaled(
				self.uiTimelineVisualization.width(),
				self.uiTimelineVisualization.height(),
				transformMode=QtCore.Qt.SmoothTransformation)
		)
		
		self.uiTimelineVisualization.update() #Invokes self.paintMotionHeatmap if needed.
	
	def paintMotionHeatmap(self, paintEvent):
		p = QPainter(self.uiTimelineVisualization)
		p.setCompositionMode(QPainter.CompositionMode_Darken)
		p.drawImage(QtCore.QPoint(0,0), self.motionHeatmap)