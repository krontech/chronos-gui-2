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
		
		self.uiFrameReadout.formatString = self.uiFrameReadout.text()
		
		self.seekRate = 60
		self.uiSeekRateDisplay.formatString = self.uiSeekRateDisplay.text()
		self.seekFaster(), self.seekSlower() #Initialize dependant state by wiggling the value around. Ideally, we'd just have a setSeekRate function. ¯\_(ツ)_/¯
		
		
		self.seekForwardTimer = QtCore.QTimer()
		self.seekForwardTimer.timeout.connect(self.updateBattery)
		self.seekForwardTimer.setInterval(16) #ms, 1/frame hopefully
		
		self.uiSeekBackward.pressed.connect( lambda: api.set({'playbackFrameDelta': -self.seekRate }))
		self.uiSeekBackward.released.connect(lambda: api.set({'playbackFrameDelta': 0 }))
		self.uiSeekForward.pressed.connect(  lambda: api.set({'playbackFrameDelta': +self.seekRate }))
		self.uiSeekForward.released.connect( lambda: api.set({'playbackFrameDelta': 0 }))
		
		self.uiSeekFaster.clicked.connect(self.seekFaster)
		self.uiSeekSlower.clicked.connect(self.seekSlower)
		
		self.uiSave.clicked.connect(lambda: api.control('saveRegions', [{}, {}]))
		
		self.uiSavedFileSettings.clicked.connect(lambda: window.show('file_settings'))
		self.uiDone.clicked.connect(window.back)
		
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
		self.uiSeekSlider.valueChanged.connect(lambda f: api.set({'playbackFrame': f}))
		api.observe('totalPlaybackFrames', self.onRecordingLengthChange)
		api.observe('playbackFrame', self.updateCurrentFrame)
		
		self.motionHeatmap = QImage() #Updated by updateMotionHeatmap, used by self.paintMotionHeatmap.
		self.uiTimelineVisualization.paintEvent = self.paintMotionHeatmap
		
		
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		api.set({'currentCameraState': 'playback'})
		self.updateBatteryTimer.start()
		self.updateBattery()
		self.updateMotionHeatmap()
		#Set camera to video playback mode here.
		
	def onHide(self):
		self.updateBatteryTimer.stop()
		api.set({'currentCameraState': 'pre-recording'})
	
	def updateBattery(self):
		self.uiBatteryReadout.setText(
			self.uiBatteryReadout.formatString.format(
				api.get('batteryCharge')*100 ) )
	
	def updateMotionHeatmap(self) -> None:
		"""Repaint the motion heatmap when we enter this screen.
			
			We never record while on the playback screen, so we don't
			have to live-update here. This is partially due to the
			fact that the camera is modal around this, it can either
			record xor playback."""
		
		heatmapHeight = 16
		
		motionData = QByteArray.fromRawData(api.control('waterfallMotionMap', 'placeholder', 400)["heatmap"]) # 16×(n<1024) heatmap. motionData: {"startFrame": int, "endFrame": int, "heatmap": QByteArray}
		assert len(motionData) % heatmapHeight == 0, f"Incompatible heatmap size {len(motionData)}; must be a multiple of {heatmapHeight}."
		
		self.motionHeatmap = (
			QImage( #Rotated 90°, since the data is packed line-by-line. We'll draw it counter-rotated.
				heatmapHeight,
				len(motionData)//heatmapHeight,
				QImage.Format_Grayscale8)
			.transformed(QTransform().rotate(-90).scale(-1,1))
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
	
	@pyqtSlot(int, name="onRecordingLengthChange")
	@silenceCallbacks('uiSeekSlider')
	def onRecordingLengthChange(self, newRecordingLength):
		self.uiSeekSlider.setMaximum(newRecordingLength)
		self.isVisible() and self.updateMotionHeatmap() #Don't update motion heatmap if not visible. It's actually a little expensive.
	
	@pyqtSlot(int, name="setCurrentFrame")
	@silenceCallbacks('uiSeekSlider', 'uiFrameReadout')
	def updateCurrentFrame(self, frame):
		self.uiSeekSlider.setValue(frame)
		
		#TODO DDR 2018-11-19: This is very slow, tanking the framerate. Why is that?
		self.uiFrameReadout.setText(self.uiFrameReadout.formatString % (frame, self.uiSeekSlider.maximum()))
	
	def seekFaster(self):
		if self.seekRate < 2000:
			self.seekRate *= 2
			self.uiSeekSlower.setEnabled(True)	
		
		if self.seekRate < 2000:
			self.uiSeekFaster.setEnabled(True)
		else:
			self.uiSeekFaster.setEnabled(False)
		
		self.uiSeekSlider.setPageStep(self.seekRate * 5) #Multiplier: Compensate for key repeat delay.
		self.uiSeekRateDisplay.setText(self.uiSeekRateDisplay.formatString % self.seekRate)
		
	def seekSlower(self):
		if self.seekRate / 2 == self.seekRate // 2:
			self.seekRate //= 2
			self.uiSeekFaster.setEnabled(True)
		
		if self.seekRate / 2 == self.seekRate // 2:
			self.uiSeekSlower.setEnabled(True)
		else:
			self.uiSeekSlower.setEnabled(False)
		
		self.uiSeekSlider.setPageStep(self.seekRate * 5) #Multiplier: Compensate for key repeat delay.
		self.uiSeekRateDisplay.setText(self.uiSeekRateDisplay.formatString % self.seekRate)
			