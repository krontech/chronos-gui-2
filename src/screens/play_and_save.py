# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QByteArray
from PyQt5.QtGui import QImage, QTransform, QPainter, QColor, QPainterPath, QBrush

from debugger import *; dbg

import api
from api import silenceCallbacks


class PlayAndSave(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/play_and_save.ui", self)
		
		self.recordedSegments = []
		self.totalRecordedFrames = 0
		
		#Use get and set marked regions, they redraw.
		self.markedRegions = [] #{mark start, mark end, segment ids, segment name}
		self.markedRegions = [{'mark end': 3184, 'segment ids': ['ldPxTT5R'], 'segment name': 'Clip 1', 'mark start': 0}, {'mark end': 41128, 'segment ids': ['KxIjG09V'], 'segment name': 'Clip 2', 'mark start': 35821}, {'mark end': 41128, 'segment ids': ['ldPxTT5R', 'KxIjG09V'], 'segment name': 'Clip 3', 'mark start': 0}]
		self.markedStart = None #Note: Mark start/end are reversed if start is after end.
		self.markedEnd = None
		
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
		
		self.uiSeekBackward.pressed.connect( lambda: api.set({'playbackFramerate': -self.seekRate }))
		self.uiSeekBackward.released.connect(lambda: api.set({'playbackFramerate': 0 }))
		self.uiSeekForward.pressed.connect(  lambda: api.set({'playbackFramerate': +self.seekRate }))
		self.uiSeekForward.released.connect( lambda: api.set({'playbackFramerate': 0 }))
		
		self.uiSeekFaster.clicked.connect(self.seekFaster)
		self.uiSeekSlower.clicked.connect(self.seekSlower)
		
		self.uiSave.clicked.connect(lambda: api.control('saveRegions', [{}, {}]))
		
		self.uiSavedFileSettings.clicked.connect(lambda: window.show('file_settings'))
		self.uiDone.clicked.connect(window.back)
		
		self.uiSeekSlider.setStyleSheet(
			self.uiSeekSlider.styleSheet() + f"""
				/* ----- Play And Save Screen Styling ----- */
				
				Slider::handle:horizontal {{
					image: url({"../../" if self.uiSeekSlider.showHitRects else ""}assets/images/handle-bars-156x61+40.png); /* File name fields: width x height + horizontal padding. */
					margin: -200px -40px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
				}}
				
				Slider::groove {{
					border: none;
				}}
			""")
		self.uiSeekSlider.valueChanged.connect(lambda f: api.set({'playbackFrame': f}))
		api.observe('totalRecordedFrames', self.onRecordingLengthChange)
		api.observe('playbackFrame', self.updateCurrentFrame)
		
		self.motionHeatmap = QImage() #Updated by updateMotionHeatmap, used by self.paintMotionHeatmap.
		self.uiTimelineVisualization.paintEvent = self.paintMotionHeatmap
		
		#Timeline marks are purely visual.
		self.uiMarkedRegionVisualization.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
		
		self.uiEditMarkedRegions.formatString = self.uiEditMarkedRegions.text()
		
		self.updateMarkedRegions()
		
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		api.set({'videoState': 'playback'})
		self.updateBatteryTimer.start()
		self.updateBattery()
		
		data = api.get(['recordedSegments', 'totalRecordedFrames']) #No destructuring bind in python. ð­
		self.recordedSegments = data['recordedSegments']
		self.totalRecordedFrames = data['totalRecordedFrames']
		
		self.updateMotionHeatmap()
		#Set camera to video playback mode here.
		
	def onHide(self):
		self.updateBatteryTimer.stop()
	
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
		
		motionData = QByteArray.fromRawData(api.control('waterfallMotionMap', {'segment':'placeholder', 'startFrame':400})["heatmap"]) # 16×(n<1024) heatmap. motionData: {"startFrame": int, "endFrame": int, "heatmap": QByteArray}
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
		
		#Draw the scrollbar motion heatmap.
		p.setCompositionMode(QPainter.CompositionMode_Darken)
		p.drawImage(QtCore.QPoint(0,0), self.motionHeatmap)
		
		#Mark the heatmap segments.
		p.setCompositionMode(QPainter.CompositionMode_SourceOver)
		p.setPen(QColor(255,255,255,255//2))
		
		path = QPainterPath()
		for border in [rs['start'] for rs in self.recordedSegments[1:]]:
			x = round(border / self.totalRecordedFrames * self.uiTimelineVisualization.width())+0.5
			path.moveTo(x, 0); path.lineTo(x, self.uiTimelineVisualization.height())
		p.drawPath(path)
		
	
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
			