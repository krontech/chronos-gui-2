# -*- coding: future_fstrings -*-

from time import time

from PyQt5.QtWidgets import QWidget, QLabel #QGestureEvent doesn't work.
from PyQt5.QtCore import QSize, Qt

from chronosGui2.debugger import *; dbg
import chronosGui2.settings as settings
from theme import theme
from chronosGui2 import delay
try:
	import chronosGui2.api as api; api.apiValues.get('videoZoom') #DDR 2020-01-15: import and *test*, as Foobar's singleton refactor seems to have made this import but fail to populate.
except Exception:
	#We don't want the lack of an API to fail us in Qt Designer. However, do warn.
	import logging
	logging.getLogger('Chronos.api').warn('Unable to import api, DirectAPILinkPlugin disabled. (Some widgets will not have any effect when used.)')
	api = None



class InteractiveVideoArea(QWidget):
	def sizeHint(self):
		return QSize(141, 141)
	
	zoomLabelTemplate = "🔎 {zoom:0.1f}x Preview Zoom"

	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)

		# API init.
		self._customStyleSheet = self.styleSheet() #always '' for some reason
		
		if showHitRects:
			self.setStyleSheet(f"""
				background: rgba(0,0,0,128);
				border: 4px solid black;
			""")
		
		self.zoomLabel = QLabel(self)
		def setZoomLabelStyle(name):
			theme_ = theme(name)
			self.zoomLabel.setStyleSheet(f"""
				color: {theme_.text};
				background-color: {theme_.interactiveVideoArea.chickletBackground};
				border: 1px solid {theme_.border};
				margin: 10px 5px;
				padding: 5px 10px;
				border-radius: 17px;
			""")
		settings.observe('theme', 'dark', setZoomLabelStyle)
		self.zoomLabel.setText(self.zoomLabelTemplate.format(zoom=2))
		self.zoomLabel.show()
		
		if showHitRects: #Make black background show up in Designer. Must be async for some reason.
			delay(self, 0, lambda: self.setAutoFillBackground(True))
		
		if api:
			self.lastClickTime = 0
			api.observe('videoZoom', self.updateVideoZoom)
			
			self.grabGesture(Qt.PinchGesture)
	
	
	if api:
		def showEvent(self, evt):
			api.video().call('set', {'videoZoom': 1})
			api.video().call('configure', {
				'xoff': max(0, min(self.x(), 800-self.width())),
				'yoff': max(0, min(self.y(), 480-self.height())),
				'hres': max(200, min(self.width(), 800)),
				'vres': max(200, min(self.height(), 480)),
			})
		
		
		def mousePressEvent(self, evt):
			clickTimeDelta = time() - self.lastClickTime
			self.lastClickTime = time()
			if clickTimeDelta < 0.5:
				#self.lastClickTime = 0 #Uncomment to disable triple-tap to zoom out.
				self.nextZoomLevel(evt)
		
		#Don't use this, because the timeout is too low for fingers. Set in x11 somewhere, writing mousePressEvent was easier that changing it (and deploying those changes reliably).
		#def mouseDoubleClickEvent(self, evt):
		
		
		def nextZoomLevel(self, *_):
			"""When double-clicked, set the zoom level to the next."""
			if not self.isEnabled(): #(But not if disabled.)
				return
			
			zoomLevels = sorted([1, 4, self.oneToOneZoomLevel()])
			zoom = api.apiValues.get('videoZoom')
			closestZoom = sorted(zoomLevels, key=lambda zl:abs(zl-zoom))[0]
			nextZoomLevel = zoomLevels[(zoomLevels.index(closestZoom)+1) % len(zoomLevels)]
			api.video().call('set', {'videoZoom': nextZoomLevel})
		
		
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
			if api.apiValues.get('videoZoom') == 1:
				self.zoomLabel.hide()
			else:
				self.zoomLabel.show()
			
			self.zoomLabel.setText(
				self.zoomLabelTemplate.format(
					zoom=self.realZoomLevel() ) )
		
		
		def resizeEvent(self, evt):
			"""Update the video zoom text on widget resize.
				
				Although we never resize widgets, they get placed after getting
				constructed so the zoom calculation is incorrect the first go-around."""
			
			self.updateVideoZoom()
			return super().resizeEvent(evt)
