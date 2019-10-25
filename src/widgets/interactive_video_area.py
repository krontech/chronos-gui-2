# -*- coding: future_fstrings -*-

from time import time

from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import QSize, QEvent, Qt
import PyQt5.QtGui as QtGui

from debugger import *; dbg
from animate import delay
try:
	import api2 as api
except Exception:
	#We don't want the lack of an API to fail us in Qt Designer. However, do warn.
	log.warn('Unable to import api, DirectAPILinkPlugin disabled. (Some widgets will not have any effect when used.)')
	api = None



class InteractiveVideoArea(QWidget):
	def sizeHint(self):
		return QSize(141, 141)
	
	zoomLabelTemplate = "🔎 {zoom:0.1f}x Zoom"

	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		self._customStyleSheet = self.styleSheet() #always '' for some reason
		if showHitRects:
			self.setStyleSheet(f"""
				background: rgba(0,0,0,128);
				border: 4px solid black;
			""")
		
		
		self.zoomLabel = QLabel(self)
		self.zoomLabel.setStyleSheet(f"""
			color: white;
			background-color: rgba(0,0,0,128);
		""")
		self.zoomLabel.setText(self.zoomLabelTemplate.format(zoom=2))
		self.zoomLabel.show()
		
		
		if showHitRects: #Make black background show up in Designer. Must be async for some reason.
			delay(self, 0, lambda: self.setAutoFillBackground(True))
		
		if api:
			self.lastClickTime = 0
			api.observe('videoZoom', self.updateVideoZoom)
	
	
	def showEvent(self, evt):
		log.print('SHOW EVENT')
		api.video.call('set', {'videoZoom': 1})
		api.video.call('configure', {
			'xoff': max(0, min(self.x(), 800-self.width())),
			'yoff': max(0, min(self.y(), 480-self.height())),
			'hres': max(200, min(self.width(), 800)),
			'vres': max(200, min(self.height(), 480)),
		})
		
		
	if api:
		def event(self, evt: QEvent):
			#add zoom here
			
			return super().event(evt)
		
		
		def mousePressEvent(self, evt):
			clickTimeDelta = time() - self.lastClickTime
			self.lastClickTime = time()
			if clickTimeDelta < 0.5:
				self.lastClickTime = 0
				self.doubleClickHandler(evt)
		
		#Don't use this, because the timeout is too low for fingers. Set in x11 somewhere, writing mousePressEvent was easier that changing it (and deploying those changes reliably).
		#def mouseDoubleClickEvent(self, evt):
		#	print('double click!')
		
		def doubleClickHandler(self, evt): #This never gets called by Qt, so we have to call it ourselves.
			"""When double-clicked, set the zoom level to the next."""
			zoomLevels = sorted([1, 4, self.oneToOneZoomLevel()])
			zoom = api.apiValues.get('videoZoom')
			closestZoom = sorted(zoomLevels, key=lambda zl:abs(zl-zoom))[0]
			nextZoomLevel = zoomLevels[(zoomLevels.index(closestZoom)+1) % len(zoomLevels)]
			api.video.call('set', {'videoZoom': nextZoomLevel})
		
		
		def oneToOneZoomLevel(self):
			"""Return the "natural" zoom of the video.
				
				This is the zoom level at which the recorded pixels have a 1:1
				correspondance with those on the screen."""
				
			res = api.apiValues.get('resolution')
			return min(
				res['hRes'] / self.width(),
				res['vRes'] / self.height(),
			)
		
		def realZoomLevel(self):
			return api.apiValues.get('videoZoom') / self.oneToOneZoomLevel()
		
		def updateVideoZoom(self, *_):
			self.zoomLabel.setText(
				self.zoomLabelTemplate.format(
					zoom=self.realZoomLevel() ) )
		
		def resizeEvent(self, evt):
			self.updateVideoZoom()
			return super().resizeEvent(evt)