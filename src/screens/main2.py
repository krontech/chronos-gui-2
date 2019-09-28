# -*- coding: future_fstrings -*-

import logging; log = logging.getLogger('Chronos.gui')
from re import match as regex_match, search as regex_search

from PyQt5 import uic, QtCore
from PyQt5.QtCore import QPoint, QSize
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor

from debugger import *; dbg
import settings
#import animate
import api2 as api

RECORDING_MODES = {'START/STOP':1, 'SOFT_TRIGGER':2, 'VIRTUAL_TRIGGER':3}
RECORDING_MODE = RECORDING_MODES['START/STOP']


class Main(QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/main2.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self._window = window
		
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
		
		
		#Focus peaking colour
		focusColor = ''
		def updateFocusColor(color):
			nonlocal focusColor
			target = getattr(self, f"ui{color.title()}FocusPeaking", None)
			if target: #Find the colour of the panel to be highlighted.
				match = regex_search(r'background:\s*?([#\w]+)', target.customStyleSheet)
				assert match, f"Could not find background color of {target.objectName()}. Check the background property of it's customStyleSheet."
				focusColor = match.group(1)
			else: #Just pass through whatever the colour is.
				focusColor = color
			
			self.uiFocusPeakingColor.update()
		api.observe('focusPeakingColor', updateFocusColor)
			
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
		
		
		#Black Cal
		self.uiBlackCal.clicked.connect(lambda:
			api.control.call('startCalibration', {
				'blackCal': True }) )
		
		
		#White Bal
		self.uiWhiteBalance.clicked.connect(lambda:
			api.control.call('startCalibration', {
				'startAutoWhiteBalance': True }) )
		
		#You can't adjust the colour of a monochromatic image.
		#Hide white balance, revealing trigger/io button.
		if api.getSync('sensorColorPattern') == 'mono':
			self.uiWhiteBalance.hide()
		
		
		#Trigger/IO
		self.uiTriggers.clicked.connect(lambda:
			window.show('triggers_and_io') )
		
		
		#Exposure
		exposureUnit = 'ms' #One of 'ms', 'deg', or 'pct'.
		exposureTemplate = self.uiExposure.text()
		
		exposureNsMin = 0
		exposureNs = 0
		exposureNsMax = 0
		
		def updateExposureText():
			self.uiExposure.setText(
				exposureTemplate.format(
					name = {
						'ms': 'Exposure',
						'pct': 'Exposure',
						'deg': 'Shutter Angle',
					}[exposureUnit],
					exposure = {
						'ms': f'{exposureNs/1e3:0.2f}ms',
						'pct': f'{round(exposureNs/(exposureNsMax-exposureNsMin)*100)}%',
						'deg': f'{round(exposureNs/(exposureNsMax-exposureNsMin)*360)}%', #TODO DDR 2019-09-27: Is this actually the way to calculate shutter angle?
					}[exposureUnit],
				)
			)
		
		#In Python 3.7: Use api.observe('exposureMin', lambda ns: exposureNSMin := ns) and give exposureNSMin a setter?
		def updateExposureNsMin(ns):
			nonlocal exposureNsMin
			exposureNsMin = ns
			updateExposureText()
		api.observe('exposureMin', updateExposureNsMin)
		
		def updateExposureNs(ns):
			nonlocal exposureNs
			exposureNs = ns
			updateExposureText()
		api.observe('exposurePeriod', updateExposureNs)
		
		def updateExposureNsMax(ns):
			nonlocal exposureNsMax
			exposureNsMax = ns
			updateExposureText()
		api.observe('exposureMax', updateExposureNsMax)
		
		#TODO DDR 2019-09-27: Make this pop up the exposure menu.
		self.uiExposure.clicked.connect(lambda:
			window.show('recording_settings') )
		
		
		#Resolution
		resolutionTemplate = self.uiResolution.text()
		
		hRes = 0
		vRes = 0
		fps = 0
		
		def updateResolutionText():
			self.uiResolution.setText(
				resolutionTemplate.format(
					hRes=hRes, vRes=vRes, fps=fps ) )
		
		def updateFps(framePeriodNs):
			nonlocal fps
			fps = 1e9 / framePeriodNs
			updateResolutionText()
		api.observe('framePeriod', updateFps)
		
		def updateResolution(resolution):
			nonlocal hRes, vRes
			hRes = resolution['hRes']
			vRes = resolution['vRes']
			updateResolutionText()
		api.observe('resolution', updateResolution)
		
		self.uiResolution.clicked.connect(lambda:
			window.show('recording_settings') )
		
		
		#Menu
		#TODO DDR 2019-09-27 make dropdown menu
		
		
		#Battery
		self._batteryTemplate = self.uiBattery.text()
		self._batteryCharge = self.uiBattery.text()
		
		self._batteryPollTimer = QtCore.QTimer()
		self._batteryPollTimer.timeout.connect(self.updateBatteryCharge)
		self._batteryPollTimer.setTimerType(QtCore.Qt.VeryCoarseTimer) #Infrequent, wake as little as possible.
		self._batteryPollTimer.setInterval(3600) #We display percentages. We update in tenth-percentage increments.
		
		
		#Record / stop
		self.uiRecordTemplate = self.uiRecord.text()
		self.uiRecord.clicked.connect(self.toggleRecording)
		
		api.observe('state', self.onStateChange)
		
		#Play & save
		
		
		#Storage media
		uiExternalMediaTemplate = self.uiExternalMedia.text()
		externalMediaUUID = ''
		externalMediaRatioFull = -1 #Don't draw the bar if negative.
		
		def updateExternalMediaPercentFull(percent):
			nonlocal externalMediaRatioFull
			if externalMediaRatioFull != percent:
				externalMediaRatioFull = percent
				self.uiExternalMedia.update()
		
		
		self.uiExternalMedia.setText("No Save\nMedia Found") #Without this, there is an unavoidable FOUC unless we call df sychronously. So we lie and just don't detect it at first. 😬
		def updateExternalMediaText():
			"""Update the external media text. This will called every few seconds to update the %-free display. Also repaints %-bar."""
			partitions = ([
				partition
				for partition in api.externalPartitions.list()
				if partition['uuid'] == externalMediaUUID
			] or api.externalPartitions.list())[:1]
			if not partitions:
				updateExternalMediaPercentFull(-1)
				self.uiExternalMedia.setText(
					"No Save\nMedia Found" )
			else:
				partition = partitions[0]
				api.externalPartitions.usageFor(partition['device'], lambda space: (
					updateExternalMediaPercentFull(space['used']/space['total']),
					self.uiExternalMedia.setText(
						uiExternalMediaTemplate.format(
							externalStorageIdentifier = partition['name'] or f"{round(partition['size'] / 1e9):1.0f}GB Storage Device",
							percentFull = round(space['used']/space['total'] * 100),
							hoursSaved = -1, minutesSaved = 0, secondsSaved = 0, #TODO: Calculate bits per second recorded and apply it here to the partition usage and total.
							hoursTotal = -1, minutesTotal = 0, secondsTotal = 0,
						)
					)
				))
		self.updateExternalMediaText = updateExternalMediaText #oops, assign this to self so we can pre-call the timer on show.
		
		def updateExternalMediaUUID(uuid):
			self.externalMediaUUID = uuid
			updateExternalMediaText()
		settings.observe('preferredFileSavingUUID', '', updateExternalMediaUUID)
		
		api.externalPartitions.observe(lambda partitions:
			updateExternalMediaText() )
		
		self._externalMediaUsagePollTimer = QtCore.QTimer()
		self._externalMediaUsagePollTimer.timeout.connect(updateExternalMediaText)
		self._externalMediaUsagePollTimer.setTimerType(QtCore.Qt.VeryCoarseTimer) #Infrequent, wake as little as possible.
		self._externalMediaUsagePollTimer.setInterval(15000) #This should almost never be needed, it just covers if another program is writing or deleting something from the disk.
		
		def uiExternalMediaPaintEvent(evt, meterPaddingX=15, meterOffsetY=2, meterHeight=10):
			"""Draw the disk usage bar on the external media button."""
			type(self.uiExternalMedia).paintEvent(self.uiExternalMedia, evt) #Invoke the superclass to - hopefully - paint the rest of the button before we deface it with our square.
			if externalMediaRatioFull == -1:
				return
			
			midpoint = self.uiExternalMedia.geometry().size()/2 + QSize(0, self.uiExternalMedia.touchMargins()['top']/2)
			type(self.uiExternalMedia).paintEvent(self.uiExternalMedia, evt) #Invoke the superclass to - hopefully - paint the rest of the button before we deface it with our square.
			p = QPainter(self.uiExternalMedia)
			p.fillRect( #xywh
				meterPaddingX,
				midpoint.height() + meterOffsetY,
				#TODO DDR 2019-09-27: When we know how long the current recorded clip is, in terms of external media capacity, add it as a white rectangle here.
				0, #(midpoint.width() - meterPaddingX) * 2 * externalMediaRatioFull + ???,
				meterHeight,
				QColor('white')
			)
			p.fillRect( #xywh
				meterPaddingX,
				midpoint.height() + meterOffsetY,
				(midpoint.width() - meterPaddingX) * 2 * externalMediaRatioFull,
				meterHeight,
				QColor('#00b800')
			)
			p.setPen(QPen(QColor('black')))
			p.setBrush(QBrush(QColor('transparent')))
			p.drawRect( #xywh
				meterPaddingX,
				midpoint.height() + meterOffsetY,
				(midpoint.width() - meterPaddingX) * 2,
				meterHeight
			)
		self.uiExternalMedia.paintEvent = uiExternalMediaPaintEvent
		
		self.uiExternalMedia.clicked.connect(lambda:
			window.show('file_settings') )
	
	
	
	def onShow(self):
		self.updateBatteryCharge2(api.getSync('batteryChargeNormalized'))
		self._batteryPollTimer.start()
		
		self.updateExternalMediaText()
		self._externalMediaUsagePollTimer.start()
	
	def onHide(self):
		self._batteryPollTimer.stop()
		self._externalMediaUsagePollTimer.stop()
	
	
	
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
	
	
	def updateBatteryCharge(self):
		api.get('batteryChargeNormalized').then(
			self.updateBatteryCharge2 )
	def updateBatteryCharge2(self, charge):
		self._batteryCharge = charge #0..1
		
		self.uiBattery.setText(
			self._batteryTemplate.format(
				round(charge*100) ) )
	
	
	def toggleRecording(self, *_):
		"""Hard start or stop recording. Doesn't use trigger/io signals."""
		
		if RECORDING_MODE != RECORDING_MODES['START/STOP']:
			return
		
		if api.apiValues.get('state') == 'idle':
			self.startRecording()
		else:
			self.stopRecording()
	
	
	#Invoked by hardware button, in ~/src/main.py.
	def publicToggleRecordingState(self, *_):
		"""Switch the camera between 'not recording' and 'recording'."""
		
		if RECORDING_MODE != RECORDING_MODES['START/STOP']:
			return
		
		self.toggleRecording()
		
		#If we're not on this screen when the red record button is pressed, go there.
		if self._window.currentScreen != 'main':
			self._window.show('main')
	
	@staticmethod
	def setVirtualTrigger(state: bool):
		"""Set the virtual trigger signal high or low.
			
			May or may not start a recording, depending on how
			trigger/io is set up.
			
			(See trigger/io screen for details.)"""
		
		#Can't use self.uiRecord.setText text here becasue we don't
		#know what the virtual trigger is actually hooked up to, on
		#what delay, so we have to wait for the signal. (We could,
		#but writing that simulation would be a lot of work.)
		
		if RECORDING_MODE == RECORDING_MODES['START/STOP']:
			pass #Taken care of by publicToggleRecordingState
		
		elif RECORDING_MODE == RECORDING_MODES['SOFT_TRIGGER']:
			raise ValueError('Soft trigger not available in FPGA.')
		
		elif RECORDING_MODE == RECORDING_MODES['VIRTUAL_TRIGGER']:
			virtuals = settings.value('virtually triggered actions', {})
			if virtuals:
				api.setSync('ioMapping', dump('new io mapping', {
					action: { 
						'source': 'alwaysHigh' if state else 'none',
						'invert': config['invert'],
						'debounce': config['debounce'],
					} for action, config in virtuals.items()
				}))
			else:
				#TODO: Log warning visually for operator, not just to console.
				log.warn('No virtual triggers configured!')
		
		else:
			raise ValueError(F'Unknown RECORDING_MODE: {RECORDING_MODE}.')
	
	
	def publicStartVirtualTrigger(self, *_):
		self.setVirtualTrigger(True)
	
	def publicStopVirtualTrigger(self, *_):
		self.setVirtualTrigger(False)
	
	
	def onStateChange(self, state):
		#This text update takes a little while to fire, so we do it in the start and stop recording functions as well so it's more responsive when the operator clicks.
		self.uiRecord.setText(
			self.uiRecordTemplate.format(
				state = 'Record' if state == 'idle' else 'Stop    ' ) )
		
		if state == 'idle' and settings.value('autoSaveVideo', False): #[autosave]
			self._window.show('play_and_save')
	
	
	def startRecording(self):
		self.uiRecord.setText(
			self.uiRecordTemplate.format(state='Stop    ') ) #Show feedback quick, the signal takes a noticable amount of time.
		api.control.callSync('startRecording')
	
	def stopRecording(self):
		self.uiRecord.setText(
			self.uiRecordTemplate.format(state='Record') )
		api.control.callSync('stopRecording')