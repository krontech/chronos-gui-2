# -*- coding: future_fstrings -*-

import logging; log = logging.getLogger('Chronos.gui')
from re import match as regex_match, search as regex_search

from PyQt5 import uic, QtCore
from PyQt5.QtCore import QPoint, QSize
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor

from debugger import *; dbg
#import animate
import api2 as api


class Main(QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/main2.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		
		#############################
		#   Button action binding   #
		#############################
		
		#Debug buttons. (These are toggled on the factory settings screen.)
		self.uiDebugA.clicked.connect(self.makeFailingCall)
		self.uiDebugB.clicked.connect(lambda: window.show('test'))
		self.uiDebugC.setFocusPolicy(QtCore.Qt.NoFocus) #Break into debugger without loosing focus, so you can debug focus issues.
		self.uiDebugC.clicked.connect(lambda: self and window and dbg()) #"self" is needed here, won't be available otherwise.
		self.uiDebugD.clicked.connect(QApplication.closeAllWindows)
		
		
		#Occasionally, the touch screen will report a spurious touch event on the top-right corner. This should prevent that. Since the record button is there now, this is actually very important.
		self.uiErrantClickCatcher.mousePressEvent = (lambda evt:
			log.warn('Errant click blocked. [WpeWCY]'))
		
		
		#Zeebs
		api.observe('zebraLevel', lambda intensity:
			self.uiZebraStripes.setCheckState(
				0 if not intensity else 2 ) )
		
		self.uiZebraStripes.stateChanged.connect(lambda state: 
			api.set({'zebraLevel': state/2}) )
		
		
		#Focus peaking
		#Use for focus peaking drop-down.
		#api.observe('focusPeakingLevel', lambda intensity:
		#	self.uiFocusPeakingIntensity.setCurrentIndex(
		#		round((1-intensity) * (self.uiFocusPeakingIntensity.count()-1)) ) )
		#
		#self.uiFocusPeakingIntensity.currentIndexChanged.connect(lambda index:
		#	api.set({'focusPeakingLevel': 1-(index/(self.uiFocusPeakingIntensity.count()-1))} ) )
		
		api.observe('focusPeakingLevel', lambda intensity:
			self.uiFocusPeaking.setCheckState(
				0 if not intensity else 2 ) )
		
		self.uiFocusPeaking.stateChanged.connect(lambda state: 
			api.set({'focusPeakingLevel': (state/2) * 0.2}) )
		
		self.hideFocusPeakingColorMenu()
		self.uiFocusPeakingColor.clicked.connect(
			self.toggleFocusPeakingColorMenu)
		
		focusColor = ''
		def setFocusColor(color):
			nonlocal focusColor
			target = getattr(self, f"ui{color.title()}FocusPeaking", None)
			if target: #Find the colour of the panel to be highlighted.
				match = regex_search(r'background:\s*?([#\w]+)', target.customStyleSheet)
				assert match, f"Could not find background color of {target.objectName()}. Check the background property of it's customStyleSheet."
				focusColor = match.group(1)
			else: #Just pass through whatever the colour is.
				focusColor = color
			
			self.uiFocusPeakingColor.update()
			
		api.observe('focusPeakingColor', setFocusColor)
		def uiFocusPeakingColorPaintEvent(evt, rectSize=24):
			"""Draw the little coloured square on the focus peaking button."""
			midpoint = self.uiFocusPeakingColor.geometry().size()/2 + QSize(0, self.uiFocusPeakingColor.touchMargins()['top']/2)
			type(self.uiFocusPeakingColor).paintEvent(self.uiFocusPeakingColor, evt) #Invoke the superclass to - hopefully - paint the rest of the button before we deface it with our square.
			p = QPainter(self.uiFocusPeakingColor)
			p.setPen(QPen(QColor('black')))
			p.setBrush(QBrush(QColor(focusColor)))
			p.drawRect( #xywh
				midpoint.width() - rectSize/2, midpoint.height() - rectSize/2,
				rectSize, rectSize )
		self.uiFocusPeakingColor.paintEvent = uiFocusPeakingColorPaintEvent
		
		
		#Focus peaking color menu
		api.observe('focusPeakingColor', self.updateFocusPeakingColor)
		
		for child in self.uiFocusPeakingColorMenu.children():
			match = regex_match(r'^ui(.*?)FocusPeaking$', child.objectName())
			match and child.clicked.connect(
				(lambda color: #Capture color from for loop.
					lambda: api.set({'focusPeakingColor': color})
				)(match.group(1).lower()) )
		
		
		
		
	
	def onShow(self):
		pass
	
	def onHide(self):
		pass
	
	
	
	def makeFailingCall(self):
		"""Debug button A: place a test call to the API."""
		
		api.control.call(
			'get', ['batteryChargePercentage']
		).then(lambda data:
			log.print(f'Test failed: Data ({data}) was returned.')
		).catch(lambda err:
			log.print(f'Test passed: Error ({err}) was returned.')
		)
	
	
	def hideFocusPeakingColorMenu(self):
		#TODO DDR 2019-09-27: Make this work right.
		self.uiFocusPeakingColorMenu.move(360, 480)
		self.uiFocusPeakingColorMenu.hide()
		
	def showFocusPeakingColorMenu(self):
		#TODO DDR 2019-09-27: Make this work right.
		self.uiFocusPeakingColorMenu.move(360, 330)
		self.uiFocusPeakingColorMenu.show()
	
	def toggleFocusPeakingColorMenu(self):
		#TODO DDR 2019-09-27: Make this work right. ie, animate, close when you tap away, etc. Basically reword animate.
		if dump('toggling', self.uiFocusPeakingColorMenu.isVisible()):
			self.hideFocusPeakingColorMenu()
		else:
			self.showFocusPeakingColorMenu()
	
	
	def updateFocusPeakingColor(self, color: str):
		"""Update the black selection square's position."""
		
		box = self.uiFocusPeakingColorSelectionIndicator
		boxSize = QPoint(
			box.geometry().width(),
			box.geometry().height() )
		
		target = getattr(self, f"ui{color.title()}FocusPeaking", None)
		if target:
			box.move(target.geometry().bottomRight() - boxSize + QPoint(1,1))
			box.show()
		else:
			log.warn(f'unknown focus peaking color {color}')
			box.hide()