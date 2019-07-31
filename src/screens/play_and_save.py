# -*- coding: future_fstrings -*-
from random import sample
from datetime import datetime

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QByteArray, QRect
from PyQt5.QtGui import QImage, QTransform, QPainter, QColor, QPainterPath, QBrush, QStandardItemModel, QStandardItem, QIcon, QIconEngine

from debugger import *; dbg

import api2
from animate import MenuToggle, delay
from widgets.line_edit import LineEdit
from widgets.button import Button
import settings



def hsva(h,s,v,a=255):
	"""Convenience function normalising QColor.fromHsv weirdness.
		
		QT interperets hsv saturation and value inverse of the rest of the world.
		Flip these values, and wrap hue because we use non-zero-indexed arcs."""
	return QColor.fromHsv(h % 360, s, v, a)


def randomCharacters(count: int):
	"""Return a random string without lookalike characters, 1/l, 0/O, etc."""
	return ''.join(sample('0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ', count))

segmentData = [{'start': 0, 'hres': 200, 'id': 'ldPxTT5R', 'end': int(1e10), 'vres': 300, 'milliframerate': 12580000.0}]



class PlayAndSave(QtWidgets.QDialog):
	saveRegionMarkerHeight = 12
	saveRegionMarkerOffset = 7
	saveRegionBorder = 1
	#Choose well-separated random hues, then fill in the gaps. Avoid green; that indicates saving for now.
	saveRegionHues = sample(range(180, 421, 60), 5) + sample(range(210, 421, 60), 4)
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/play_and_save.ui", self)
		
		self._window = window
		
		self.recordedSegments = []
		self.totalRecordedFrames = 0
		
		self.videoState = None
		self.regionBeingSaved = None
		
		#Use get and set marked regions, they redraw.
		self.markedRegions = [
			{'region id': 'aaaaaaaa', 'hue': 240, 'mark end': 19900, 'mark start': 13002, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 1'},
			{'region id': 'aaaaaaab', 'hue': 300, 'mark end': 41797, 'mark start': 40597, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 2'},
			{'region id': 'aaaaaaac', 'hue': 420, 'mark end': 43897, 'mark start': 41797, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 3'},
			{'region id': 'aaaaaaad', 'hue': 180, 'mark end': 53599, 'mark start': 52699, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 4'},
			{'region id': 'aaaaaaae', 'hue': 360, 'mark end': 52699, 'mark start': 51799, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 5'},
			{'region id': 'aaaaaaaf', 'hue': 210, 'mark end': 80000, 'mark start': 35290, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 6'},
			{'region id': 'aaaaaaag', 'hue': 390, 'mark end': 42587, 'mark start': 16716, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 7'},
			{'region id': 'aaaaaaah', 'hue': 270, 'mark end': 25075, 'mark start': 17016, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 8'},
			{'region id': 'aaaaaaai', 'hue': 330, 'mark end': 36617, 'mark start': 28259, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 9'},
			{'region id': 'aaaaaaaj', 'hue': 240, 'mark end': 39005, 'mark start': 32637, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 10'},
			{'region id': 'aaaaaaak', 'hue': 300, 'mark end': 39668, 'mark start': 36219, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 11'},
			{'region id': 'aaaaaaal', 'hue': 420, 'mark end': 39068, 'mark start': 37868, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 12'},
			{'region id': 'aaaaaaam', 'hue': 180, 'mark end': 13930, 'mark start': 0,     'saved': 0.0, 'highlight': 0, 'segment ids': ['ldPxTT5R', 'KxIjG09V'], 'region name': 'Clip 13'},
		]
		self.markedRegions = [
			{'region id': 'aaaaaaaa', 'hue': 240, 'mark end': 199, 'mark start': 130, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 1'},
			{'region id': 'aaaaaaab', 'hue': 300, 'mark end': 417, 'mark start': 105, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 2'},
		]
		self.markedRegions = []
		self.markedStart = None #Note: Mark start/end are reversed if start is after end.
		self.markedEnd = None
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		#Put the video here.
		self.videoArea = self.uiVideoArea.geometry()
		self.uiVideoArea.deleteLater() #Don't need this any more!
		
		self.uiBatteryReadout.anchorPoint = self.uiBatteryReadout.rect()
		self.uiBatteryReadout.formatString = self.uiBatteryReadout.text()
		self.uiBatteryReadout.clicked.connect(lambda: window.show('power'))
		self.updateBatteryTimer = QtCore.QTimer()
		self.updateBatteryTimer.timeout.connect(self.updateBattery)
		self.updateBatteryTimer.setInterval(2000) #ms
		
		self.labelUpdateIdleDelayTimer = QtCore.QTimer() #Used to skip calling the api alltogether when seeking.
		self.labelUpdateIdleDelayTimer.setInterval(32)
		self.labelUpdateIdleDelayTimer.setSingleShot(True)
		self.labelUpdateTimer = QtCore.QTimer()
		self.labelUpdateTimer.setInterval(32) #ms, cap at 60fps. (Technically this is just a penalty, we need to *race* the timer and the dbus call but we can't easily do that because we need something like .~*Promise.all()*~. for that and it's a bit of a pain in the neck to construct right now.)
		self.labelUpdateTimer.setSingleShot(True) #Start the timer again after the update.
		lastKnownFrame = -1
		lastKnownFilesaveStatus = False
		iteration = 0
		noLoopUpdateCounter = 0 #When < 0, don't update slider to avoid the following issue: 1) Slider is updated. 2) D-Bus message is sent. 3) Slider is updated several times more. 4) D-Bus message returns and updates slider. 5) Slider is updated from old position, producing a jerk or a jump.
		def checkLastKnownFrame(status=None):
			nonlocal iteration
			nonlocal lastKnownFrame
			nonlocal lastKnownFilesaveStatus
			nonlocal noLoopUpdateCounter
			
			if not self.isVisible(): #Stop updates if screen has been exited.
				return
			
			iteration += 1
			noLoopUpdateCounter += 1
			#log.print(f'iteration {iteration} (f{lastKnownFrame}, {lastKnownFilesaveStatus})')
			#log.print(f'loop {noLoopUpdateCounter}')
			
			if status and self.videoState in ('play', 'filesave'):
				if status['position'] != lastKnownFrame:
					lastKnownFrame = status['position']
					self.uiCurrentFrame.setValue(lastKnownFrame)
					if noLoopUpdateCounter > 0:
						self.uiSeekSlider.blockSignals(True)
						self.uiSeekSlider.setValue(lastKnownFrame)
						self.uiSeekSlider.blockSignals(False)
				
				if status['filesave'] != lastKnownFilesaveStatus:
					lastKnownFilesaveStatus = status['filesave']
					if not lastKnownFilesaveStatus:
						#Restore the seek rate display to the manual play rate.
						self.uiSeekRate.setValue(self.seekRate)
				
				if self.videoState == 'filesave':
					region = [r for r in self.markedRegions if r['region id'] == self.regionBeingSaved][:1]
					if region: #Protect against resets in the middle of saving.
						region = region[0]
						region['saved'] = (lastKnownFrame - region['mark start']) / (region['mark end'] - region['mark start'])
				
				#Set the seek rate counter back to what the camera operator set it to.
				if lastKnownFilesaveStatus:
					self.uiSeekRate.setValue(status['framerate'])
			
			#Loop after a short timeout, if the screen is still visible.
			if noLoopUpdateCounter > 0:
				self.labelUpdateTimer.start()
			else:
				self.labelUpdateIdleDelayTimer.start()
		self.labelUpdateIdleDelayTimer.timeout.connect(checkLastKnownFrame)
		self.labelUpdateTimer.timeout.connect(lambda: #Now, the timer is not running, so we can't just stop it to stop this process. We may be waiting on the dbus call instead.
			api2.video.call('status').then(checkLastKnownFrame) )
		
		self.uiCurrentFrame.suffixFormatString = self.uiCurrentFrame.suffix()
		self.uiCurrentFrame.valueChanged.connect(lambda f: 
			self.uiCurrentFrame.hasFocus() and api2.video.call('playback', {'position':f}) )
		
		self.seekRate = 60
		self.uiSeekRate.setValue(self.seekRate)
		
		self.uiSeekBackward.pressed.connect( lambda: api2.video.call('playback', {'framerate': -self.seekRate}))
		self.uiSeekBackward.released.connect(lambda: api2.video.call('playback', {'framerate': 0}))
		self.uiSeekForward.pressed.connect(  lambda: api2.video.call('playback', {'framerate': +self.seekRate}))
		self.uiSeekForward.released.connect( lambda: api2.video.call('playback', {'framerate': 0}))
		
		self.uiSeekFaster.clicked.connect(self.seekFaster)
		self.uiSeekSlower.clicked.connect(self.seekSlower)
		
		self.uiMarkStart.clicked.connect(self.markStart)
		self.uiMarkEnd.clicked.connect(self.markEnd)
		
		self.uiSave.clicked.connect(self.onSaveClicked)
		self.uiSaveCancel.clicked.connect(self.cancelSave)
		self.uiSaveCancel.hide()
		
		self.uiSavedFileSettings.clicked.connect(lambda: window.show('file_settings'))
		self.uiDone.clicked.connect(window.back)
		
		self.uiSeekSlider.setStyleSheet( #Can't use setCustomStylesheet because slider is not a child of touch_margin_plugin.
			self.uiSeekSlider.styleSheet() + f"""
				/* ----- Play And Save Screen Styling ----- */
				
				
				/*Heatmap got delayed. Don't style for now… (Remove the "X-"s to apply again.)*/
				Slider::handle:horizontal {{
					image: url({"../../" if self.uiSeekSlider.showHitRects else ""}assets/images/handle-bars-156x61+40.png); /* File name fields: width x height + horizontal padding. */
					margin: -200px -40px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
				}}
				
				Slider::groove {{
					border: none;
				}}
			""")
		#Heatmap got delayed. Don't report different size/touchMargins for heatmap styling.
		self.uiSeekSlider.sliderSize = lambda: QtCore.QSize(156, 61) #Line up focus ring.
		#self.uiSeekSlider.touchMargins = lambda: { "top": 10, "left": 10, "bottom": 10, "right": 10, } #Report real margins.
		#self.uiSeekSlider.focusGeometryNudge = (0,0,0,0)
		self.uiSeekSlider.touchMargins = lambda: { "top": 10, "left": 0, "bottom": 10, "right": 0, } #Report real margins.
		self.uiSeekSlider.debounce.sliderMoved.connect(lambda frame: 
			api2.video.callSync('playback', {'position': frame}) )
		self.uiSeekSlider.debounce.sliderMoved.connect(lambda frame: 
			self.uiCurrentFrame.setValue(frame) )
		#last_perf = perf_counter()
		#def countPerfs(*_):
		#	nonlocal last_perf
		#	log.print(f'update took {(perf_counter() - last_perf)*1000}ms')
		#	last_perf = perf_counter()
		#self.uiSeekSlider.debounce.sliderMoved.connect(countPerfs)
		def updateNoLoopUpdateCounter(*_):
			nonlocal noLoopUpdateCounter
			noLoopUpdateCounter = -10 #Delay updating until the d-bus call has had a chance to return.
		self.uiSeekSlider.debounce.sliderMoved.connect(updateNoLoopUpdateCounter)
		
		self.motionHeatmap = QImage() #Updated by updateMotionHeatmap, used by self.paintMotionHeatmap.
		self.uiTimelineVisualization.paintEvent = self.paintMotionHeatmap
		self.uiTimelineVisualization.hide() #Heatmap got delayed. Hide for now, some logic still depends on it.
		
		#Set up for marked regions.
		self._tracks = [] #Used as cache for updateMarkedRegions / paintMarkedRegions.
		self.uiEditMarkedRegions.formatString = self.uiEditMarkedRegions.text()
		self.uiMarkedRegionVisualization.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
		self.uiMarkedRegionVisualization.paintEvent = self.paintMarkedRegions
		self.regionsListModel = QStandardItemModel(parent=self.uiMarkedRegions)
		self.uiMarkedRegions.setModel(self.regionsListModel)
		self.regionsListModel.rowsRemoved.connect(self.regionListElementDeleted)
		self.regionsListModel.dataChanged.connect(self.regionListElementChanged)
		self.updateMarkedRegions()
		
		self.markedRegionMenu = MenuToggle(
			menu = self.uiMarkedRegionsPanel,
			button = self.uiEditMarkedRegions,
			xRange = (-self.uiMarkedRegionsPanel.width(), -1),
			duration = 30,
		)
		#delay(self, 1, self.markedRegionMenu.toggle) #mmm, just like a crappy javascript app - work around a mysterious black bar appearing on the right-hand side of the window.
		
		self.uiMarkedRegionsPanelHeader.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		self.uiMarkedRegionsPanelHeaderX.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		self.uiMarkedRegionPanelClose.clicked.connect(self.markedRegionMenu.forceHide)
		self.uiMarkedRegions.setItemDelegate(EditMarkedRegionsItemDelegate())
		self.lastSelectedRegion = None
		self.uiMarkedRegions.clicked.connect(self.selectMarkedRegion)
		
		api2.observe('videoState', self.onVideoStateChangeAlways)
		api2.observe('state', self.onStateChangeAlways)
		
		api2.signal.observe('sof', self.onSOF)
		api2.signal.observe('eof', self.onEOF)
		
	def onShow(self):
		status = api2.video.callSync('status')
		
		#Don't update the labels while hidden. But do show with accurate info when we start.
		api2.video.call('configure', {
			'xoff': self.videoArea.x(),
			'yoff': self.videoArea.y(),
			'hres': self.videoArea.width(),
			'vres': self.videoArea.height(),
		})
		
		if not status['filesave']:
			api2.video.call('playback', {'framerate':0})
		
		self.updateBatteryTimer.start()
		self.updateBattery()
		
		self.recordedSegments = segmentData #api2.get('recordedSegments')
		
		self.checkMarkedRegionsValid()
		
		#Recalculate width width of frame readout and battery readout, choosing max.
		#This tends to jump around otherwise, unlike the edit marked regions button, so keep it static.

		
		geom = self.uiBatteryReadout.geometry()
		geom.setLeft(
			geom.right() 
			- 10*2 - 20 - 2 #qss margin, click margin, magic
			- self.uiBatteryReadout.fontMetrics().width(
				self.uiBatteryReadout.formatString.format(100)
			)
		)
		self.uiBatteryReadout.setGeometry(geom)
		
		self.updateMotionHeatmap()
		
		self.labelUpdateTimer.start() #This will stop on its own.
		
		self.uiSeekSlider.setValue(status['position'])
		self.uiCurrentFrame.setValue(status['position'])
		
		api2.observe('state', self.onStateChangeWhenScreenActive)
		
	def onHide(self):
		self.updateBatteryTimer.stop()
		api2.unobserve('state', self.onStateChangeWhenScreenActive)
	
	
	def updateBattery(self):
		api2.control.call(
			'get', ['batteryChargePercent']
		).then(lambda data:
			self.uiBatteryReadout.setText(
				self.uiBatteryReadout.formatString.format(data['batteryChargePercent']) )
		)
	
	
	def updateMotionHeatmap(self) -> None:
		"""Repaint the motion heatmap when we enter this screen.
			
			We never record while on the playback screen, so we don't
			have to live-update here. This is partially due to the
			fact that the camera is modal around this, it can either
			record xor playback."""
		
		return #Heatmap got delayed. Just return for now…
		
		heatmapHeight = 16
		
		motionData = QByteArray.fromRawData(api2.control('waterfallMotionMap', {'segment':'placeholder', 'startFrame':400})["heatmap"]) # 16×(n<1024) heatmap. motionData: {"startFrame": int, "endFrame": int, "heatmap": QByteArray}
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
		return #Heatmap got delayed. Just return for now…
		
		if not self.totalRecordedFrames:
			return
		
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
	
	def seekFaster(self):
		if self.seekRate < 2000:
			self.seekRate *= 2
			self.uiSeekSlower.fake_disability = False
		
		if self.seekRate < 2000:
			self.uiSeekFaster.fake_disability = False
		else:
			self.uiSeekFaster.fake_disability = True
		
		self.uiSeekSlider.setPageStep(self.seekRate * 5) #Multiplier: Compensate for key repeat delay.
		self.uiSeekRate.setValue(self.seekRate)
		
	def seekSlower(self):
		if self.seekRate / 2 == self.seekRate // 2:
			self.seekRate //= 2
			self.uiSeekFaster.fake_disability = False
		
		if self.seekRate / 2 == self.seekRate // 2:
			self.uiSeekSlower.fake_disability = False
		else:
			self.uiSeekSlower.fake_disability = True
			self.uiSeekSlower.setFocus()
		
		self.uiSeekSlider.setPageStep(self.seekRate * 5) #Multiplier: Compensate for key repeat delay.
		self.uiSeekRate.setValue(self.seekRate)
	
	
	def markStart(self):
		"""Set mark in."""
		self.markedStart = self.uiSeekSlider.value()
		
		if self.markedStart == self.markedEnd:
			self.markedEnd = None
		
		self.addMarkedRegion()
		self.uiTimelineVisualization.update()
	
	def markEnd(self):
		"""Set mark out."""
		self.markedEnd = self.uiSeekSlider.value()
		
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
			"region id": randomCharacters(8),
			"mark start": self.markedStart,
			"mark end": self.markedEnd,
			"segment ids": [
				segment['id']
				for segment in segmentData#api2.get('recordedSegments') 
				if not (segment['start'] >= self.markedEnd or segment['end'] < self.markedStart)
			],
			"region name": f'Clip {len(self.markedRegions)+1}',
			"saved": 0., #ratio between 0 and 1
			"highlight": 0, #-1 for black, 0 for none, 1 for white
			"hue": self.saveRegionHues[len(self.markedRegions) % len(self.saveRegionHues)],
		}]
		
		self.markedStart, self.markedEnd = None, None
		
		log.print(f'Marked region {self.markedRegions}')
		
		self.updateMarkedRegions()
	
	
	def updateMarkedRegions(self):
		"""Recalculate marked regions and mark in/out marker."""
		
		#Update the marked region count.
		self.uiEditMarkedRegions.setText(
			self.uiEditMarkedRegions.formatString % len(self.markedRegions) )
		
		self.uiEditMarkedRegions.resize(
			self.uiEditMarkedRegions.fontMetrics().width(self.uiEditMarkedRegions.text())
				+ self.uiEditMarkedRegions.touchMargins()['right'] 
				+ (10*2) #padding
				+ (1*2) #border?
				+ 1, #magic.
			self.uiEditMarkedRegions.height(),
		)
		
		#Set up entries in the marked regions panel.
		model = self.uiMarkedRegions.model()
		model.clear()
		for region in self.markedRegions:
			model.appendRow(QStandardItem(
				QIcon(RegionIconEngine(region)), 
				region["region name"],
			))
		
		#Update the marked region visualisation, under the frame slider.
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
		
		if not self.totalRecordedFrames:
			return
		
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
				regionRect = QRect(
					f2px(region['mark start']),
					trackOffset + self.saveRegionBorder,
					f2px(region['mark end'] - region['mark start']),
					self.saveRegionMarkerHeight,
				)
				
				if region['saved'] < 1: #Draw coloured, unsaved marked region.
					p.setPen(hsva(
						region['hue'],
						{-1:150, 0:230, 1:255}[region['highlight']],
						{-1:160, 0:190, 1:100}[region['highlight']],
					))
					p.setBrush(QBrush(hsva(
						region['hue'], 
						{-1:0, 0:153, 1:255}[region['highlight']], 
						{-1:0, 0:230, 1:255}[region['highlight']],
					)))
					p.setClipRect(regionRect.adjusted(regionRect.width() * region['saved'],0, 0,0))
					p.drawRect(regionRect)
				
				if region['saved'] > 0: #Draw green, saved marked region.
					p.setPen(hsva(
						120, #green
						{-1:150, 0:230, 1:255}[region['highlight']],
						{-1:160, 0:190, 1:100}[region['highlight']],
					))
					p.setBrush(QBrush(hsva(
						120, 
						{-1:0, 0:153, 1:255}[region['highlight']], 
						{-1:0, 0:230, 1:255}[region['highlight']],
					)))
					p.setClipRect(regionRect.adjusted(0,0, -regionRect.width() * (1-region['saved']),0))
					p.drawRect(regionRect)
			
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
	
	
	def selectMarkedRegion(self, pos: QtCore.QModelIndex):
		if self.lastSelectedRegion == pos.row():
			return
		else:
			self.lastSelectedRegion = pos.row()
		
		def assign(self, index, status):
			"""Hack to work around not being able to assign in a lambda."""
			self.markedRegions[index]['highlight'] = status
			self.uiMarkedRegionVisualization.update()
		
		def assignCatpureIndex(self, index, status):
			"""Hack to capture the value of index in a closure.
				
				Index which will otherwise get changed by the time we use it, if it is used in a lambda."""
			return lambda: assign(self, index, status)
		
		for index in range(len(self.markedRegions)):
			if index == pos.row():
				duration = 400
				self.markedRegions[index]['highlight'] = -1
				delay(self, 1/3 * duration, assignCatpureIndex(self, index, 1))
				delay(self, 2/3 * duration, assignCatpureIndex(self, index, -1))
				delay(self, 3/3 * duration, assignCatpureIndex(self, index, 1))
			else:
				self.markedRegions[index]['highlight'] = 0
		
		
	def regionListElementDeleted(self, parent, first, last):
		"""Sync the python-side region list with the qt-side region list."""
		self.markedRegions = self.markedRegions[:first] + self.markedRegions[last+1:]
		self.updateMarkedRegions() #Cached indexes have changed.
		
	def regionListElementChanged(self, topLeft, bottomRight, _roles):
		"""Sync the python-side region list with the qt-side region list."""
		assert topLeft.column() == 0 and bottomRight.column() == 0, "Only list data supported."
		assert topLeft.row() == bottomRight.row(), "Multi-row editing not supported."
		index = topLeft.row()
		self.markedRegions[index]['region name'] = self.regionsListModel.item(index).text()
	
	class NoRegionMarked(Exception):
		pass
	
	class NoSaveMedia(Exception):
		pass
	
	def saveMarkedRegion(self):
		"""Save the next marked region.
			
			Note: This method is invoked from a button and from a state-change
			watcher. This means that, once started, it will be called for each
			marked region sequentially as saving completes."""
		uuid = settings.value('preferredFileSavingUUID', '')
		if uuid in [part['uuid'] for part in api2.externalPartitions.list()]:
			#Use the operator-set partition.
			partition = [part for part in api2.externalPartitions.list() if part['uuid'] == uuid][0]
		elif api2.externalPartitions.list()[-1:]:
			#The operator-set partition is not mounted. Use the most recent partition instead.
			partition = api2.externalPartitions.list()[-1]
		else:
			#No media is usable for saving.
			raise type(self).NoSaveMedia()
		
		roi = [r for r in self.markedRegions if r['saved'] == 0][:1]
		if not roi:
			#No regions marked for saving.
			raise type(self).NoRegionMarked()
		roi = roi[0]
		self.regionBeingSaved = roi['region id']
		self.uiSeekSlider.setEnabled(False)
		
		now = datetime.now()
		res = api2.getSync('resolution') #TODO DDR 2019-07-26 Get this from the segment metadata we don't have as of writing.
		roi['file'] = f'''{
			partition['path'].decode('utf-8')
		}/{
			settings.value('savedVideoName', r'vid_%date%_%time%')
				.replace(r'%region name%', str(roi['region name']))
				.replace(r'%date%', now.strftime("%Y-%m-%d"))
				.replace(r'%time%', now.strftime("%H-%M-%S"))
				.replace(r'%start frame%', str(roi['mark start']))
				.replace(r'%end frame%', str(roi['mark end']))
		}{
			settings.value('savedVideoFileExtention', '.mp4')
		}'''
		
		self.uiSave.hide()
		self.uiSaveCancel.show()
		
		#regions are like {'region id': 'aaaaaaag', 'hue': 390, 'mark end': 42587, 'mark start': 16716, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 7'},
		api2.video.callSync('recordfile', {
			'filename': roi['file'],
			'format': {
				'.mp4':'h264', 
				'.dng':'dng', 
				'.tiff':'tiff', 
				'.raw':'byr2',
			}[settings.value('savedVideoFileExtention', '.mp4')],
			'start': roi['mark start'],
			'length': roi['mark end'] - roi['mark start'],
			'framerate': settings.value('savedFileFramerate', 30), #TODO DDR 2019-07-24 read this from recording settings
			'bitrate': min(
				res['hRes'] * res['vRes'] * api2.getSync('frameRate') * settings.value('savedFileBPP', 0.7),
				settings.value('savedFileMaxBitrate', 40) * 1000000.0,
			)
		})
		
	def cancelSave(self, evt):
		#Reset the region saved amount, since the file is now deleted.
		region = [r for r in self.markedRegions if r['region id'] == self.regionBeingSaved][:1]
		if region: #Protect against resets in the middle of saving.
			region = region[0]
			#Saved files are partially retained. Don't reset save progress. region['saved'] = 0.
		
		self.regionBeingSaved = None
		self.uiSeekSlider.setEnabled(True)
		api2.video.call('stop')
		
		#Set the UI back to seek mode.
		self.uiSeekRate.setValue(self.seekRate)
		self.uiSave.show()
		self.uiSaveCancel.hide()
		
	
	@pyqtSlot(str, float, name="onRegionSaving")
	def onRegionSaving(self, regionId, ratioSaved):
		[r for r in self.markedRegions if r['region id'] == regionId][0]['saved'] = ratioSaved
	
	
	
	@pyqtSlot(str, float)
	def onVideoStateChangeAlways(self, state): #Always fires, even when screen closed.
		self.videoState = state
		
		#If we were saving a region, progress to the next region.
		if state == 'play' and self.regionBeingSaved:
			region = [r for r in self.markedRegions if r['region id'] == self.regionBeingSaved][:1]
			if region: #Protect against resets in the middle of saving.
				region = region[0]
				#{'region id': 'aaaaaaaa', 'hue': 240, 'mark end': 199, 'mark start': 130, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 1'},
				region['saved'] = 1.0
				try:
					self.saveMarkedRegion()
				except type(self).NoRegionMarked:
					self.regionBeingSaved = None
					self.uiSeekSlider.setEnabled(True)
	
	
	@pyqtSlot(str, float)
	def onStateChangeAlways(self, state): #Only fires when screen open. Fires once when opened.
		if state == 'recording' and (self.markedRegions or self.uiSeekSlider.value()):
			self.markedRegions.clear()
			self.updateMarkedRegions()
			api2.setSync('playbackPosition', 0)
			self.uiSeekSlider.setValue(0)
	
	
	@pyqtSlot(str, float)
	def onStateChangeWhenScreenActive(self, state): #Only fires when screen open. Fires once when opened.
		api2.video.call('status').then(self.onStateChangeWhenScreenActive2)
	def onStateChangeWhenScreenActive2(self, status):
		#Filesave doesn't actually affect anything, just the transition to/from playback.
		if status['filesave']:
			return
		
		#Reset number of frames.
		self.uiSeekSlider.setMaximum(status['totalFrames'])
		self.uiSeekSlider.setMaximum(status['totalFrames'])
		self.updateMotionHeatmap()
		
		
		self.totalRecordedFrames = status['totalFrames']
		self.uiCurrentFrame.setMaximum(status['totalFrames'])
		self.uiCurrentFrame.setSuffix(
			self.uiCurrentFrame.suffixFormatString % status['totalFrames']
		)
		geom = self.uiCurrentFrame.geometry()
		geom.setLeft(
			geom.right() 
			- 10*2 - 5 #qss margin, magic
			- self.uiCurrentFrame.fontMetrics().width(
				self.uiCurrentFrame.prefix()
				+ str(status['totalFrames'])
				+ self.uiCurrentFrame.suffixFormatString % status['totalFrames']
			)
		)
		self.uiCurrentFrame.setGeometry(geom)
		
		
		if settings.value('autoSaveVideo', False) and not self.markedRegions: #[autosave]
			self.markedStart = self.uiSeekSlider.minimum()
			self.markedEnd = self.uiSeekSlider.maximum()
			self.addMarkedRegion()
			self.saveMarkedRegion()
	
	
	def onSOF(self, state):
		if state['filesave']: #Check event is relevant to saving.
			self.uiSeekSlider.setEnabled(False)
			self.uiSave.hide()
			self.uiSaveCancel.show()
		
	def onEOF(self, state):
		if state['filesave']: #Check event is relevant to saving.
			self.regionBeingSaved = None
			self.uiSeekSlider.setEnabled(True)
			self.uiSave.show()
			self.uiSaveCancel.hide()
			
			#Close this screen and return to the main screen for more recording, now that we're done saving. [autosave]
			noUnsavedRegionsLeft = not [r for r in self.markedRegions if r['saved'] == 0]
			if noUnsavedRegionsLeft and settings.value('resumeRecordingAfterSave', False):
				self._window.show('main')
	
	
	def onSaveClicked(self, evt):
		try:
			self.saveMarkedRegion()
		except e:
			raise e #TODO: Display proper errors.
			
	
class EditMarkedRegionsItemDelegate(QtWidgets.QStyledItemDelegate):
	class EditorAndDeleterFactory(QtWidgets.QItemEditorFactory):
		def createEditor(self, userType: int, parent: QtWidgets.QWidget):
			editor = QtWidgets.QWidget(parent)
			
			lineEdit = LineEdit(editor)
			editor.lineEdit = lineEdit #Because lineEdit.setObjectName('lineEdit') and editor.findChild(QtCore.QObject, 'lineEdit') don't work together to return anything other than None.
			lineEdit.setCustomStyleSheet('''
				/*Hide touch-margin styles.*/
				LineEdit {
					border-width: 0;
					margin-left: 15px; margin-right: 0; margin-top: 0; margin-bottom: 0;
				}
			''')
			
			delete = Button(editor)
			editor.delete = delete
			delete.setText('×')
			delete.sizeHint = lambda: QtCore.QSize(delete.parent().height(), delete.parent().height())
			delete.setCustomStyleSheet('''
				Button { 
					color: darkred;
					border-width: 0;
					margin-left: 0; margin-right: 0; margin-top: 0; margin-bottom: 0;
				}
			''')
			
			layout = QtWidgets.QHBoxLayout(editor)
			layout.addWidget(lineEdit)
			layout.addWidget(delete)
			layout.setStretch(1,0)
			layout.setSpacing(0)
			layout.setContentsMargins(0,0,0,0)
			
			return editor
	
	
	def __init__(self):
		super().__init__()
			
		self.setItemEditorFactory(
			EditMarkedRegionsItemDelegate.EditorAndDeleterFactory() )
	
	
	def setEditorData(self, editor: EditorAndDeleterFactory, index: QtCore.QModelIndex):
		editor.lineEdit.setText(index.data())
		
		def deleteRow(self):
			editor.parent().parent().setFocus() #Return focus to the list.
			editor.setParent(None) #If we remove the editor parent, we segfault.
			index.model().removeRow(index.row())
		editor.delete.clicked.connect(deleteRow)
	
	
	def setModelData(self, editor: EditorAndDeleterFactory, model: QtCore.QModelIndex, index: QtCore.QModelIndex):
		model.setData(index, editor.lineEdit.text(), QtCore.Qt.EditRole)
	
	def updateEditorGeometry(self, editor: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
		"""Set the editor to be the full size of the row.
			
			By default, the editor takes up the content size of the row. But the
			editor needs to have it's own padding, since otherwise you're just
			clicking on the row behind the editor."""
		
		editor.setGeometry(option.rect)


class RegionIconEngine(QIconEngine):
	size = QtCore.QSize(10,45)
	
	def __init__(self, region):
		super().__init__()
		self.region = region
	
	def actualSize(self, size: QtCore.QSize, _mode, _state) -> QtCore.QSize:
		#This is the size of the rect passed to self.paint().
		return self.size
	
	def availableSizes(self, _mode, _state) -> list:
		#Should be called to query available icon sizes; isn't.
		return [self.size]
	
	def key(self):
		#Identify this icon engine.
		return str(self.region['hue'])
	
	def paint(self, p: QPainter, rect: QtCore.QRect, _mode, _state):
		"""Draw an icon the colour of the rect.
			
			Used by the edit marked regions panel."""
		
		p.setPen(hsva(self.region['hue'], 230, 190))
		p.setBrush(QBrush(hsva(self.region['hue'], 153, 230)))
		p.drawRect(rect)