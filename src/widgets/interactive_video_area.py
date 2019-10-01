# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtProperty, QSize

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

	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		self._customStyleSheet = self.styleSheet() #always '' for some reason
		if showHitRects:
			self.setStyleSheet(f"""
				background: rgba(0,0,0,128);
				border: 4px solid black;
			""")
		
		if showHitRects: #Make black background show up in Designer. Must be async for some reason.
			delay(self, 0, lambda: self.setAutoFillBackground(True))
	
	def showEvent(self, evt):
		api and api.video.call('configure', {
			'xoff': max(0, min(self.x(), 800-self.width())),
			'yoff': max(0, min(self.y(), 480-self.height())),
			'hres': max(200, min(self.width(), 800)),
			'vres': max(200, min(self.height(), 480)),
		})