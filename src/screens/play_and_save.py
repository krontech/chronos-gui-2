# -*- coding: future_fstrings -*-
from random import sample

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QByteArray
from PyQt5.QtGui import QImage, QTransform, QPainter, QColor, QPainterPath, QBrush, QStandardItemModel, QStandardItem

from debugger import *; dbg

import api
from api import silenceCallbacks
from animate import MenuToggle, delay
from widgets.line_edit import LineEdit
from widgets.button import Button


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
		self.markedRegions = [] #{mark start, mark end, segment ids, region name}
		self.markedRegions = [
			{'hue': 240, 'mark end': 19900, 'mark start': 13002, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 1'},
			{'hue': 300, 'mark end': 41797, 'mark start': 40597, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 2'},
			{'hue': 420, 'mark end': 43897, 'mark start': 41797, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 3'},
			{'hue': 180, 'mark end': 53599, 'mark start': 52699, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 4'},
			{'hue': 360, 'mark end': 52699, 'mark start': 51799, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 5'},
			{'hue': 210, 'mark end': 80000, 'mark start': 35290, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 6'},
			{'hue': 390, 'mark end': 42587, 'mark start': 16716, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 7'},
			{'hue': 270, 'mark end': 25075, 'mark start': 17016, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 8'},
			{'hue': 330, 'mark end': 36617, 'mark start': 28259, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 9'},
			{'hue': 240, 'mark end': 39005, 'mark start': 32637, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 10'},
			{'hue': 300, 'mark end': 39668, 'mark start': 36219, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 11'},
			{'hue': 420, 'mark end': 39068, 'mark start': 37868, 'saved': 0.0, 'highlight': 0, 'segment ids': ['KxIjG09V'], 'region name': 'Clip 12'},
			{'hue': 180, 'mark end': 13930, 'mark start': 0,     'saved': 0.0, 'highlight': 0, 'segment ids': ['ldPxTT5R', 'KxIjG09V'], 'region name': 'Clip 13'},
		]
		self.markedStart = None #Note: Mark start/end are reversed if start is after end.
		self.markedEnd = None
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiBatteryReadout.anchorPoint = self.uiBatteryReadout.rect()
		self.uiBatteryReadout.formatString = self.uiBatteryReadout.text()
		self.uiBatteryReadout.clicked.connect(lambda: window.show('power'))
		self.updateBatteryTimer = QtCore.QTimer()
		self.updateBatteryTimer.timeout.connect(self.updateBattery)
		self.updateBatteryTimer.setInterval(2000) #ms
		
		self.uiCurrentFrame.suffixFormatString = self.uiCurrentFrame.suffix()
		self.uiCurrentFrame.valueChanged.connect(lambda f: api.set({'playbackFrame': f}))
		
		
		self.seekRate = 60
		self.uiSeekRate.setValue(self.seekRate)
		
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
		
		self.uiSave.clicked.connect(lambda: api.control('saveRegions', [{
			"start": region['mark start'],
			"end": region['mark end'],
			"path": '/dev/sda', #TODO: Retrieve this from saved file settings screen, via local settings.
			"format": {'fps': 30, 'encoding': 'h264'},
			"filename": r'普通棕色蝙蝠_%DATE%_劃分_%REGION NAME%-%START FRAME%-%END FRAME%.mp4'
				.replace(r'%REGION NAME%', region['region name']),
		} for region in self.markedRegions]))
		
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
		self.uiMarkedRegions.setModel(QStandardItemModel(parent=self.uiMarkedRegions))
		self.updateMarkedRegions()
		
		self.markedRegionMenu = MenuToggle(
			menu = self.uiMarkedRegionsPanel,
			button = self.uiEditMarkedRegions,
			xRange = (-self.uiMarkedRegionsPanel.width(), -1),
			duration = 30,
		)
		delay(self, 1, self.markedRegionMenu.toggle) #mmm, just like a crappy javascript app - work around a mysterious black bar appearing on the right-hand side of the window.
		
		self.uiMarkedRegionsPanelHeader.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		self.uiMarkedRegionsPanelHeaderX.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		self.uiMarkedRegionPanelClose.clicked.connect(self.markedRegionMenu.forceHide)
		self.uiMarkedRegions.setItemDelegate(EditMarkedRegionsItemDelegate())
		self.uiMarkedRegions.clicked.connect(self.selectMarkedRegion)
		
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		api.set({'videoState': 'playback'})
		self.updateBatteryTimer.start()
		self.updateBattery()
		
		data = api.get(['recordedSegments', 'totalRecordedFrames']) #No destructuring bind in python. 😭
		self.recordedSegments = data['recordedSegments']
		self.totalRecordedFrames = data['totalRecordedFrames']
		self.uiCurrentFrame.setMaximum(data['totalRecordedFrames'])
		self.uiCurrentFrame.setSuffix(
			self.uiCurrentFrame.suffixFormatString % data['totalRecordedFrames']
		)
		
		self.checkMarkedRegionsValid()
		
		#Recalculate width width of frame readout and battery readout, choosing max.
		#This tends to jump around otherwise, unlike the edit marked regions button, so keep it static.
		geom = self.uiCurrentFrame.geometry()
		geom.setLeft(
			geom.right() 
			- 10*2 - 5 #qss margin, magic
			- self.uiCurrentFrame.fontMetrics().width(
				self.uiCurrentFrame.prefix()
				+ str(data['totalRecordedFrames'])
				+ self.uiCurrentFrame.suffixFormatString % data['totalRecordedFrames']
			)
		)
		self.uiCurrentFrame.setGeometry(geom)
		
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
	@silenceCallbacks('uiSeekSlider', 'uiCurrentFrame')
	def updateCurrentFrame(self, frame):
		self.uiSeekSlider.setValue(frame)
		
		#TODO DDR 2018-11-19: This is very slow, tanking the framerate. Why is that?
		self.uiCurrentFrame.setValue(frame)
	
	
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
			"region name": f'Clip {len(self.markedRegions)+1}',
			"saved": 0., #ratio between 0 and 1
			"highlight": 0, #-1 for black, 0 for none, 1 for white
			"hue": self.saveRegionHues[len(self.markedRegions) % len(self.saveRegionHues)],
		}]
		
		self.markedStart, self.markedEnd = None, None
		
		pp(self.markedRegions)
		
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
			model.appendRow(QStandardItem(region["region name"]))
		
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
				#
				
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
	
	
	def selectMarkedRegion(self, pos: QtCore.QModelIndex):
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
		
		self.uiMarkedRegionVisualization.update()

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
					margin-left: 0; margin-right: 0; margin-top: 0; margin-bottom: 0;
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
		itemRect = option.rect
		itemRect.moveTop(itemRect.height() * index.row()) #all rows same size 😅
		editor.setGeometry(itemRect)