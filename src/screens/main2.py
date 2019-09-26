# -*- coding: future_fstrings -*-

import logging; log = logging.getLogger('Chronos.gui')

from PyQt5 import uic, QtCore
#from PyQt5.QtCore import QPropertyAnimation, QPoint
from PyQt5.QtWidgets import QWidget, QApplication

from debugger import *; dbg
#import animate
#import api2 as api


class Main(QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/main2.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiDebugA.clicked.connect(self.makeFailingCall)
		self.uiDebugB.clicked.connect(lambda: window.show('test'))
		self.uiDebugC.setFocusPolicy(QtCore.Qt.NoFocus) #Break into debugger without loosing focus, so you can debug focus issues.
		self.uiDebugC.clicked.connect(lambda: self and window and dbg()) #"self" is needed here, won't be available otherwise.
		self.uiDebugD.clicked.connect(QApplication.closeAllWindows)
		
		self.uiErrantClickCatcher.mousePressEvent = (lambda evt:
			log.warn('Errant click blocked. [WpeWCY]'))
		
	
	def onShow(self):
		pass
	
	def onHide(self):
		pass
	
	
	
	def makeFailingCall(self):
		"""Debug function to test a call."""
		api2.control.call(
			'get', ['batteryChargePercentage']
		).then(lambda data:
			log.print(f'Test failed: Data ({data}) was returned.')
		).catch(lambda err:
			log.print(f'Test passed: Error ({err}) was returned.')
		)
	
	