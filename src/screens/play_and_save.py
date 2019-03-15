# -*- coding: future_fstrings -*-
from random import sample

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QByteArray
from PyQt5.QtGui import QImage, QTransform, QPainter, QColor, QPainterPath, QBrush

from debugger import *; dbg

import api
from api import silenceCallbacks


class PlayAndSave(QtWidgets.QDialog):
	saveRegionMarkerHeight = 12
	saveRegionMarkerOffset = 7
	saveRegionBorder = 1
	#Choose well-separated random hues, then fill in the gaps. Avoid green; that indicates saving for now.
	saveRegionHues = sample(range(180, 421, 60), 5) + sample(range(210, 421, 60), 4)
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/play_and_save.ui", self)
		
		self.recordedSegments = []
		self.totalRecordedFrames = 0
		
		#Use get and set marked regions, they redraw.
		self.markedRegions = [] #{mark start, mark end, segment ids, segment name}
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
		
		self.uiMarkStart.clicked.connect(self.markStart)
		self.uiMarkEnd.clicked.connect(self.markEnd)
		
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
		
		#Set up for marked regions.
		self._tracks = [] #Used as cache for updateMarkedRegions / paintMarkedRegions.
		self.uiEditMarkedRegions.formatString = self.uiEditMarkedRegions.text()
		self.uiMarkedRegionVisualization.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
		self.uiMarkedRegionVisualization.paintEvent = self.paintMarkedRegions
		self.updateMarkedRegions()
		
		
		
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		api.set({'videoState': 'playback'})
		self.updateBatteryTimer.start()
		self.updateBattery()
		
		data = api.get(['recordedSegments', 'totalRecordedFrames']) #No destructuring bind in python. 😭
		self.recordedSegments = data['recordedSegments']
		self.totalRecordedFrames = data['totalRecordedFrames']
		self.checkMarkedRegionsValid()
		
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
			x = round(border / self.totalRecordedFrames * (self.uiTimelineVisualization.width()-1))+0.5
			path.moveTo(x, 0); path.lineTo(x, self.uiTimelineVisualization.height())
		p.drawPath(path)
		
		#Mark save start/save end.
		mark = self.markedStart if self.markedStart is not None else self.markedEnd
		if mark is not None:
			p.setPen(QColor(100,230,100,255))
			path = QPainterPath()
			x = round(mark / self.totalRecordedFrames * (self.uiTimelineVisualization.width()-1))+0.5
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
	
	
	def markStart(self):
		"""Set mark in."""
		self.markedStart = api.get('playbackFrame')
		
		if self.markedStart == self.markedEnd:
			self.markedEnd = None
		
		self.addMarkedRegion()
		self.uiTimelineVisualization.update()
	
	def markEnd(self):
		"""Set mark out."""
		self.markedEnd = api.get('playbackFrame')
		
		if self.markedStart == self.markedEnd:
			self.markedEnd = None
		
		self.addMarkedRegion()
		self.uiTimelineVisualization.update()
	
	
	def addMarkedRegion(self):
		if None in (self.markedStart, self.markedEnd): #Be careful. 0 is valid, None is not, both are falsey.
			return #No region marked.
		
		if self.markedStart > self.markedEnd:
			self.markedEnd, self.markedStart = self.markedStart, self.markedEnd
		
		self.markedRegions += [{
			"mark start": self.markedStart,
			"mark end": self.markedEnd,
			"segment ids": [
				segment['id']
				for segment in api.get('recordedSegments') 
				if not (segment['start'] >= self.markedEnd or segment['end'] < self.markedStart)
			],
			"segment name": f'Clip {len(self.markedRegions)+1}',
			"saved": 0., #ratio between 0 and 1
			"hue": self.saveRegionHues[len(self.markedRegions) % len(self.saveRegionHues)],
		}]
		
		self.markedStart, self.markedEnd = None, None
		
		self.updateMarkedRegions()
	
	
	def updateMarkedRegions(self):
		"""Recalculate marked regions and mark in/out marker."""
		
		#First thing, update the marked region count.
		self.uiEditMarkedRegions.setText(
			self.uiEditMarkedRegions.formatString % len(self.markedRegions) )
		
		#We'll assign each marked region a track. Regions can't overlap on the
		#same track. They should always use the lowest track available.
		tracks = []
		for newRegion in self.markedRegions:
			availableTrack = [
				track
				for track in tracks
				if not [ #overlapping region in track
					trackedRegion
					for trackedRegion in track
					if not (trackedRegion['mark start'] >= newRegion['mark end'] or trackedRegion['mark end'] <= newRegion['mark start'])
				][:1]
			][:1]
			
			if availableTrack:
				availableTrack[0] += [newRegion]
			else:
				tracks += [[newRegion]]
		
		#Recalculate height.
		height = self.saveRegionMarkerHeight + self.saveRegionMarkerOffset*(len(tracks)-1) + self.saveRegionBorder
		self.uiMarkedRegionVisualization.setGeometry(
			self.uiTimelineVisualization.x(),
			min(
				self.uiTimelineVisualization.y() + self.uiTimelineVisualization.height()/2 - height/2,
				self.height() - height,
			),
			self.uiTimelineVisualization.width(),
			height,
		)
		
		#Redraw
		self._tracks = tracks
		self.uiMarkedRegionVisualization.update()
	
	def paintMarkedRegions(self, evt):
		"""Draw the marked region indicators."""
		
		def f2px(frameNumber):
			"""Convert frame number to pixel coordinates."""
			return round(frameNumber / self.totalRecordedFrames * (self.uiMarkedRegionVisualization.width()-1))
		
		def hsva(h,s,v,a=255):
			"""Convenience function normalising QColor.fromHsv weirdness.
				
				QT interperets hsv saturation and value inverse of the rest of the world.
				Flip these values, and wrap hue because we use non-zero-indexed arcs."""
			return QColor.fromHsv(h % 360, s, v, a)
		
		p = QPainter(self.uiMarkedRegionVisualization)
		
		#This causes borders to get merged and generally mis-drawn.
		#Could otherwise be used to simplify math when calculating rect position.
		#p.setCompositionMode(QPainter.CompositionMode_DestinationOver)
		
		#This causes graphics glitches in 5.7 upon redraw.
		#Could otherwise be used to simplify math when calculating rect position.
		#p.scale(1,-1)
		#p.translate(0, -evt.rect().height()+1)
		
		#Draw the tracks of marked regions.
		trackOffset = -1
		for track in reversed(self._tracks):
			for region in track:
				p.setPen(hsva(region['hue'], 230, 190))
				p.setBrush(QBrush(hsva(region['hue'], 153, 230)))
				
				p.drawRect(
					f2px(region['mark start']),
					trackOffset + self.saveRegionBorder,
					f2px(region['mark end'] - region['mark start']),
					self.saveRegionMarkerHeight,
				)
			
			trackOffset += self.saveRegionMarkerOffset
	
	
	def checkMarkedRegionsValid(self):
		self.markedRegions = list([
			region 
			for region in self.markedRegions
			if set(region['segment ids']).issubset([
				segment['id']
				for segment in self.recordedSegments
			])
		])
		self.updateMarkedRegions()