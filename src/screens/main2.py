# -*- coding: future_fstrings -*-

import logging; log = logging.getLogger('Chronos.gui')
from re import match as regex_match, search as regex_search
from time import time
import math
from glob import iglob

from PyQt5 import uic, QtCore
from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QStandardItemModel, QPainterPath, QPolygonF

from debugger import *; dbg
import settings
from widgets.theme import theme
import animate
import api
import estimate_file as estimateFile

RECORDING_MODES = {'START/STOP':1, 'SOFT_TRIGGER':2, 'VIRTUAL_TRIGGER':3}
RECORDING_MODE = RECORDING_MODES['START/STOP']

#settings.setValue('theme', 'dark') #[HACK DDR 2019-11-15] patch around dark theme until it works, because the dark theme is the default.

class Main(QWidget):
	uiPowerDownThreshold = 0.05 #Used to be in API as saveAndPowerDownLowBatteryLevelNormalized, but this got taken out December 2019.
	
	def __init__(self, window):
		super().__init__()
		#uic\.loadUi\("(.*?)\.chronos\.ui", self\)
		if api.apiValues.get('cameraModel')[0:2] == 'TX':
			uic.loadUi("src/screens/main2.txpro.ui", self)
		else:
			uic.loadUi("src/screens/main2.chronos.ui", self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize()) #This is not a responsive design.
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self._window = window
		
		#Hide the fake borders if the buttons don't have borders.
		if self.uiBlackCal.hideBorder:
			self.uiBottomHorizontalLine.hide()
			self.uiBottomVerticalLine.hide()
		else:
			self.uiBottomHorizontalLine.show()
			self.uiBottomVerticalLine.show()
		
		self.uiFocusPeakingOriginalCustomStyleSheet = self.uiFocusPeaking.styleSheet()
		self.uiZebraStripesOriginalCustomStyleSheet = self.uiZebraStripes.styleSheet()
		settings.observe('theme', 'dark', lambda name: (
			self.uiFocusPeaking.setStyleSheet(
				self.uiFocusPeakingOriginalCustomStyleSheet + f"""
					CheckBox {{ background-color: {theme(name).background} }}
				"""
			),
			self.uiZebraStripes.setStyleSheet(
				self.uiZebraStripesOriginalCustomStyleSheet + f"""
					CheckBox {{ background-color: {theme(name).background} }}
				"""
			)
		))
		
		#Note start/end recording times, to display the timers.
		recordingStartTime = 0
		recordingEndTime = 0
		def updateRecordingStartTime(state):
			nonlocal recordingStartTime, recordingEndTime
			if state == 'recording':
				recordingStartTime = time()
				recordingEndTime = 0
				self.uiPlayAndSave.update()
				self.uiRecord.update()
			elif state == 'idle' and not recordingEndTime:
				recordingEndTime = time()
				self.uiPlayAndSave.update()
				self.uiRecord.update()
		api.observe('state', updateRecordingStartTime)
		
		totalFrames = api.getSync('totalFrames')
		if totalFrames == 0: #Set the length of the recording to 0, if nothing has been recorded. Otherwise, calculate what we've recorded.
			recordingStartTime = recordingEndTime
		else:
			recordingEndTime = recordingStartTime + totalFrames/api.getSync('frameRate')
		
		self.uiMenuBackground.hide()
		self.uiMenuBackground.move(0,0)
		
		lastOpenerButton = None
		
		def showMenu(button: QWidget, menu: QWidget, *_):
			nonlocal lastOpenerButton
			lastOpenerButton = button
			
			self.uiMenuBackground.show(),
			self.uiMenuBackground.raise_(),
			button.raise_(),
			menu.show(),
			menu.raise_(),
			self.focusRing.raise_(),
		self.showMenu = showMenu
			
		def hideMenu(*_):
			nonlocal lastOpenerButton
			if not lastOpenerButton:
				return
			
			self.uiMenuBackground.hide()
			self.uiFocusPeakingColorMenu.hide()
			self.uiMenuDropdown.hide()
			self.uiExposureMenu.hide()
			self.uiWhiteBalanceMenu.hide()
			lastOpenerButton.setFocus()
			
			lastOpenerButton = None
		self.hideMenu = hideMenu
		
		self.uiMenuBackground.mousePressEvent = hideMenu
		self.uiMenuBackground.focusInEvent = hideMenu
		
		
		#############################
		#   Button action binding   #
		#############################
		
		#Debug buttons. (These are toggled on the factory settings screen.)
		self.uiDebugA.clicked.connect(self.makeFailingCall)
		self.uiDebugB.clicked.connect(lambda: window.show('test'))
		self.uiDebugC.setFocusPolicy(QtCore.Qt.TabFocus) #Break into debugger without loosing focus, so you can debug focus issues.
		self.uiDebugC.clicked.connect(lambda: self and window and dbg()) #"self" is needed here, won't be available otherwise.
		self.uiDebugD.clicked.connect(QApplication.closeAllWindows)
		
		#Only show the debug controls if enabled in factory settings.
		settings.observe('debug controls enabled', False, lambda show: (
			self.uiDebugA.show() if show else self.uiDebugA.hide(),
			self.uiDebugB.show() if show else self.uiDebugB.hide(),
			self.uiDebugC.show() if show else self.uiDebugC.hide(),
			self.uiDebugD.show() if show else self.uiDebugD.hide(),
		))
		
		
		#Occasionally, the touch screen seems to report a spurious touch event on the top-right corner. This should prevent that. (Since the record button is there now, this is actually very important!)
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
		
		# Hack around API always setting focus peaking high.
		animate.delay(self, 5000, lambda: log.warn('Overriding focus peaking to 0 to work around pychronos/issues/49.'))
		animate.delay(self, 5000, lambda: api.setSync({'focusPeakingLevel': 0}))
		
		api.observe('focusPeakingLevel', lambda intensity:
			self.uiFocusPeaking.setCheckState(
				0 if not intensity else 2 ) )
		
		self.uiFocusPeaking.stateChanged.connect(lambda state: 
			api.set({'focusPeakingLevel': (state/2) * 0.2}) )
		
		
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
		
		self.uiFocusPeakingColor.clicked.connect(
			self.toggleFocusPeakingColorMenu)
		
		self.uiFocusPeakingColorMenu.hide()
		self.uiFocusPeakingColorMenu.move(360, 330)
		
		
		#Loop focus peaking color menu focus, for the jog wheel.
		self.uiMagentaFocusPeaking.nextInFocusChain = (lambda *_: 
			self.uiFocusPeakingColor
			if self.uiFocusPeakingColorMenu.isVisible() else
			type(self.uiMagentaFocusPeaking).nextInFocusChain(self.uiMagentaFocusPeaking, *_)
		)
		self.uiRedFocusPeaking.previousInFocusChain = (lambda *_: 
			self.uiFocusPeakingColor
			if self.uiFocusPeakingColorMenu.isVisible() else
			type(self.uiRedFocusPeaking).previousInFocusChain(self.uiRedFocusPeaking, *_)
		)
		self.uiFocusPeakingColor.nextInFocusChain = (lambda *_:
			self.uiRedFocusPeaking
			if self.uiFocusPeakingColorMenu.isVisible() else
			type(self.uiFocusPeakingColor).nextInFocusChain(self.uiFocusPeakingColor, *_)
		)
		self.uiFocusPeakingColor.previousInFocusChain = (lambda *_:
			self.uiMagentaFocusPeaking
			if self.uiFocusPeakingColorMenu.isVisible() else
			type(self.uiFocusPeakingColor).previousInFocusChain(self.uiFocusPeakingColor, *_)
		)
		
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
		
		
		#White Bal & Trigger/IO
		try:
			whiteBalanceTemplate = self.uiWhiteBalance.text()
			api.observe('wbTemperature', lambda temp:
				self.uiWhiteBalance.setText(
					whiteBalanceTemplate.format(temp) ))
			self.uiWhiteBalance.clicked.connect(lambda:
				api.control.call('startCalibration', {
					'startAutoWhiteBalance': True }) )
		except AssertionError:
			log.warn('Failed to observe wbTemperature. (Is it implemented yet?) Patching uiWhiteBalance…')
			self.uiWhiteBalance.setText("White\nBalance")
		
		self.uiTriggers.clicked.connect(lambda:
			window.show('triggers_and_io') )
		
		# You can't adjust the colour of a monochromatic image.
		# Hide white balance in favour of trigger/io button.
		if api.apiValues.get('sensorColorPattern') == 'mono':
			self.uiWhiteBalance.hide()
		else:
			self.uiTriggers.hide()
		
		self.uiWhiteBalanceMenu.hide()
		self.uiWhiteBalanceMenu.move(
			self.x(),
			self.uiWhiteBalance.y() - self.uiWhiteBalanceMenu.height() + self.uiWhiteBalance.touchMargins()['top'],
		)
		self.uiWhiteBalance.clicked.connect(lambda *_: 
			hideMenu()
			if self.uiWhiteBalanceMenu.isVisible() else
			showMenu(self.uiWhiteBalance, self.uiWhiteBalanceMenu)
		)
		
		#Loop white balance menu focus, for the jog wheel.
		self.uiFineTuneColor.nextInFocusChain = (lambda *_: 
			self.uiWhiteBalance
			if self.uiWhiteBalanceMenu.isVisible() else
			type(self.uiFineTuneColor).nextInFocusChain(self.uiFineTuneColor, *_)
		)
		self.uiWBPreset1.previousInFocusChain = (lambda *_: 
			self.uiWhiteBalance
			if self.uiWhiteBalanceMenu.isVisible() else
			type(self.uiWBPreset1).previousInFocusChain(self.uiWBPreset1, *_)
		)
		self.uiWhiteBalance.nextInFocusChain = (lambda *_:
			self.uiWBPreset1
			if self.uiWhiteBalanceMenu.isVisible() else
			type(self.uiWhiteBalance).nextInFocusChain(self.uiWhiteBalance, *_)
		)
		self.uiWhiteBalance.previousInFocusChain = (lambda *_:
			self.uiFineTuneColor
			if self.uiWhiteBalanceMenu.isVisible() else
			type(self.uiWhiteBalance).previousInFocusChain(self.uiWhiteBalance, *_)
		)
		
		self.uiWBPreset1.clicked.connect(lambda evt:
			api.set('wbTemperature', self.uiWBPreset1.property('temp')) )
		self.uiWBPreset2.clicked.connect(lambda evt:
			api.set('wbTemperature', self.uiWBPreset2.property('temp')) )
		self.uiWBPreset3.clicked.connect(lambda evt:
			api.set('wbTemperature', self.uiWBPreset3.property('temp')) )
		self.uiWBPreset4.clicked.connect(lambda evt:
			api.set('wbTemperature', self.uiWBPreset4.property('temp')) )
		self.uiWBPreset5.clicked.connect(lambda evt:
			api.set('wbTemperature', self.uiWBPreset5.property('temp')) )
		self.uiFineTuneColor.clicked.connect(lambda: window.show('color'))
		
		
		#Exposure
		def updateExposureSliderLimits():
			"""Update exposure text to match exposure slider, and sets the slider step so clicking the gutter always moves 1%."""
			step1percent = (self.uiExposureSlider.minimum() + self.uiExposureSlider.maximum()) // 100
			self.uiExposureSlider.setSingleStep(step1percent)
			self.uiExposureSlider.setPageStep(step1percent*10)
		
		def onExposureSliderMoved(newExposureNs):
			nonlocal exposureNs
			
			linearRatio = (newExposureNs-self.uiExposureSlider.minimum()) / (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum())
			newExposureNs = math.pow(linearRatio, 2) * self.uiExposureSlider.maximum()
			api.control.call('set', {'exposurePeriod': newExposureNs})
			
			#The signal takes too long to return, as it's masked by the new value the slider sets.
			exposureNs = newExposureNs
			updateExposureText()
		
		def updateExposureMax(newExposureNs):
			self.uiExposureSlider.setMaximum(newExposureNs)
			updateExposureSliderLimits()
		
		def updateExposureMin(newExposureNs):
			self.uiExposureSlider.setMinimum(newExposureNs)
			updateExposureSliderLimits()
		
		#Must set slider min/max before value.
		api.observe('exposureMax', updateExposureMax)
		api.observe('exposureMin', updateExposureMin)
		
		exposureUnit = 'ms' #One of 'ms', 'deg', or 'pct'.
		exposureTemplate = self.uiExposure.text()
		uiExposureInDegreesTemplate = self.uiExposureInDegrees.text()
		uiExposureInMsTemplate = self.uiExposureInMs.text()
		uiExposureInPercentTemplate = self.uiExposureInPercent.text()
		
		exposureNsMin = 0
		exposureNs = 0
		exposureNsMax = 0
		
		def updateExposureText(*_):
			exposureDeg = exposureNs/api.apiValues.get('framePeriod')*360
			exposurePct = exposureNs/(exposureNsMax or 1)*100
			exposureMs = exposureNs/1e3
			
			if exposurePct < 0:
				dbg()
			
			self.uiExposure.setText(
				exposureTemplate.format(
					name = {
						'ms': 'Exposure',
						'pct': 'Exposure',
						'deg': 'Shutter Angle',
					}[exposureUnit],
					exposure = {
						'deg': f'{exposureDeg:1.0f}°', #TODO DDR 2019-09-27: Is this actually the way to calculate shutter angle?
						'pct': f'{exposurePct:1.1f}%',
						'ms': f'{exposureMs:1.1f}ms',
					}[exposureUnit],
				)
			)
			
			self.uiExposureInDegrees.setText(
				uiExposureInDegreesTemplate.format(
					degrees = exposureDeg ) )
			
			self.uiExposureInPercent.setText(
				uiExposureInPercentTemplate.format(
					percent = exposurePct ) )
			
			self.uiExposureInMs.setText(
				uiExposureInMsTemplate.format(
					duration = exposureMs ) )
			
			linearRatio = exposureNs/(exposureNsMax-exposureNsMin)
			try:
				exponentialRatio = math.sqrt(linearRatio)
			except ValueError:
				exponentialRatio = 0
			if not self.uiExposureSlider.beingHeld:
				self.uiExposureSlider.setValue(exponentialRatio * (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum()) + self.uiExposureSlider.minimum())
			updateExposureSliderLimits()
		
		# In Python 3.7: Use api.observe('exposureMin', lambda ns: exposureNSMin := ns) and give exposureNSMin a setter?
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
		
		api.observe('framePeriod', updateExposureText)
		
		self.uiExposureMenu.hide()
		self.uiExposureMenu.move(
			self.x(),
			self.uiExposure.y() - self.uiExposureMenu.height() + self.uiExposure.touchMargins()['top'],
		)
		self.uiExposure.clicked.connect(lambda *_: 
			hideMenu()
			if self.uiExposureMenu.isVisible() else
			showMenu(self.uiExposure, self.uiExposureMenu)
		)
		
		#Loop exposure menu focus, for the jog wheel.
		self.uiExposureSlider.nextInFocusChain = (lambda *_: 
			self.uiExposure
			if self.uiExposureMenu.isVisible() else
			type(self.uiExposureSlider).nextInFocusChain(self.uiExposureSlider, *_)
		)
		self.uiExposureInDegrees.previousInFocusChain = (lambda *_: 
			self.uiExposure
			if self.uiExposureMenu.isVisible() else
			type(self.uiExposureInDegrees).previousInFocusChain(self.uiExposureInDegrees, *_)
		)
		self.uiExposure.nextInFocusChain = (lambda *_:
			self.uiExposureInDegrees
			if self.uiExposureMenu.isVisible() else
			type(self.uiExposure).nextInFocusChain(self.uiExposure, *_)
		)
		self.uiExposure.previousInFocusChain = (lambda *_:
			self.uiExposureSlider
			if self.uiExposureMenu.isVisible() else
			type(self.uiExposure).previousInFocusChain(self.uiExposure, *_)
		)
		
		def uiExposureInDegreesClicked(*_):
			nonlocal exposureUnit
			exposureUnit = 'deg'
			updateExposureText()
		self.uiExposureInDegrees.clicked.connect(
			uiExposureInDegreesClicked )
		
		def uiExposureInMsClicked(*_):
			nonlocal exposureUnit
			exposureUnit = 'ms'
			updateExposureText()
		self.uiExposureInMs.clicked.connect(
			uiExposureInMsClicked )
		
		def uiExposureInPercentClicked(*_):
			nonlocal exposureUnit
			exposureUnit = 'pct'
			updateExposureText()
		self.uiExposureInPercent.clicked.connect(
			uiExposureInPercentClicked )
		
		
		#Exposure Slider - copied from the original main.py.
		self.uiExposureSlider.debounce.sliderMoved.connect(onExposureSliderMoved)
		self.uiExposureSlider.touchMargins = lambda: {
			"top": 10, "left": 10, "bottom": 10, "right": 10
		}
		
		
		
		
		
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
		self.uiMenuDropdown.hide()
		self.uiMenuDropdown.move(
			self.uiMenuButton.x(),
			self.uiMenuButton.y() + self.uiMenuButton.height() -  self.uiMenuButton.touchMargins()['bottom'] - self.uiMenuFilter.touchMargins()['top'] - 1, #-1 to merge margins.
		)
		self.uiMenuButton.clicked.connect((lambda:
			hideMenu() 
			if self.uiMenuDropdown.isVisible() else
			showMenu(self.uiMenuButton, self.uiMenuDropdown)
		))
		
		#Loop main menu focus, for the jog wheel.
		self.uiMenuScroll.nextInFocusChain = (lambda *_: #DDR 2019-10-21: This doesn't work, and seems to break end-of-scroll progression in the menu scroll along the way.
			self.uiMenuButton
			if self.uiMenuDropdown.isVisible() else
			type(self.uiMenuScroll).nextInFocusChain(self.uiMenuScroll, *_)
		)
		self.uiMenuFilter.previousInFocusChain = (lambda *_: 
			self.uiMenuButton
			if self.uiMenuDropdown.isVisible() else
			type(self.uiMenuFilter).previousInFocusChain(self.uiMenuFilter, *_)
		)
		self.uiMenuButton.nextInFocusChain = (lambda *_:
			self.uiMenuFilter
			if self.uiMenuDropdown.isVisible() else
			type(self.uiMenuButton).nextInFocusChain(self.uiMenuButton, *_)
		)
		self.uiMenuButton.previousInFocusChain = (lambda *_:
			self.uiMenuScroll
			if self.uiMenuDropdown.isVisible() else
			type(self.uiMenuButton).previousInFocusChain(self.uiMenuButton, *_)
		)
		
		# Populate uiMenuScroll from actions.
		# Generally, anything which has a button on the main screen will be
		# hidden in this menu, which means it won't come up unless we search
		# for it. This should -- hopefully -- keep the clutter down without
		# being confusing.
		_whiteBalAvail = api.apiValues.get('sensorColorPattern') == 'mono' #Black and white models of the Chronos do not have colour to balance, so don't show that screen ever.
		_scriptsHidden = not [f for f in iglob('/var/camera/scripts/*')][:1] #Only show the scripts screen if there will be a script on it to run.
		log.print(f'_scriptsHidden {_scriptsHidden}')
		main_menu_items = [
			{'name':"About Camera",          'open':lambda: window.show('about_camera'),          'hidden': False,           'synonyms':"kickstarter thanks name credits"},
			{'name':"App & Internet",        'open':lambda: window.show('remote_access'),         'hidden': False,           'synonyms':"remote access web client network control api"},
			{'name':"Battery & Power",       'open':lambda: window.show('power'),                 'hidden': True,            'synonyms':"charge wake turn off power down"},
			{'name':"Camera Settings",       'open':lambda: window.show('user_settings'),         'hidden': False,           'synonyms':"user operator save settings"},
			{'name':"Custom Scripts",        'open':lambda: window.show('scripts'),               'hidden': _scriptsHidden,  'synonyms':"scripting bash python"},
			{'name':"Factory Utilities",     'open':lambda: window.show('service_screen.locked'), 'hidden': False,           'synonyms':"utils"},
			{'name':"Format Storage",        'open':lambda: window.show('storage'),               'hidden': True,            'synonyms':"file saving save media df mounts mounted devices thumb drive ssd sd card usb stick filesystem reformat"},
			{'name':"Interface Options",     'open':lambda: window.show('primary_settings'),      'hidden': False,           'synonyms':"rotate rotation screen set time set date"},
			{'name':"Play & Save Recording", 'open':lambda: window.show('play_and_save'),         'hidden': True,            'synonyms':"mark region saving"},
			{'name':"Record Mode",           'open':lambda: window.show('record_mode'),           'hidden': False,           'synonyms':"segmented run n gun normal"},
			{'name':"Recording Settings",    'open':lambda: window.show('recording_settings'),    'hidden': True,            'synonyms':"resolution framerate offset gain boost brightness exposure"},
			{'name':"Review Saved Videos",   'open':lambda: window.show('replay'),                'hidden': False,           'synonyms':"playback show footage saved card movie replay"},
			{'name':"Stamp Overlay",         'open':lambda: window.show('stamp'),                 'hidden': False,           'synonyms':"watermark"},
			#{'name':"Trigger Delay",        'open':lambda: window.show('trigger_delay'),         'hidden': False,           'synonyms':"wait"}, #Removed because we use the trigger/io delay block now.
			{'name':"Triggers & IO",         'open':lambda: window.show('triggers_and_io'),       'hidden': False,           'synonyms':"bnc green ~a1 ~a2 trig1 trig2 trig3 signal input output trigger delay"},
			{'name':"Update Camera",         'open':lambda: window.show('update_firmware'),       'hidden': False,           'synonyms':"firmware"},
			{'name':"Video Save Settings",   'open':lambda: window.show('file_settings'),         'hidden': True,            'synonyms':"file saving"},
		]
		if(_whiteBalAvail):
			main_menu_items += [
				{'name':"Color",             'open':lambda: window.show('white_balance'),         'hidden': True,            'synonyms':"matrix colour white balance temperature"},
			]
		
		
		menuScrollModel = QStandardItemModel(
			len(main_menu_items), 1, self.uiMenuScroll )
		for i in range(len(main_menu_items)):
			menuScrollModel.setItemData(menuScrollModel.index(i, 0), {
				Qt.DisplayRole: main_menu_items[i]['name'],
				Qt.UserRole: main_menu_items[i],
				Qt.DecorationRole: None, #Icon would go here.
			})
		self.uiMenuScroll.setModel(menuScrollModel)
		self.uiMenuScroll.clicked.connect(self.showOptionOnTap)
		self.uiMenuScroll.jogWheelClick.connect(self.showOptionOnJogWheelClick)
		
		self.uiMenuFilterIcon.setAttribute(Qt.WA_TransparentForMouseEvents) #Allow clicking on the filter icon, 🔎, to filter.
		self.uiMenuFilter.textChanged.connect(self.filterMenu)
		self.filterMenu()
		
		
		#Battery
		self._batteryCharge   = 1
		self._batteryCharging = 0
		self._batteryPresent  = 0
		self._batteryBlink = False
		self._theme = 'light'
		
		self._batteryTemplate = self.uiBattery.text()
		
		self._batteryPollTimer = QtCore.QTimer()
		self._batteryPollTimer.timeout.connect(self.updateBatteryCharge)
		self._batteryPollTimer.setTimerType(QtCore.Qt.VeryCoarseTimer) #Infrequent, wake as little as possible.
		self._batteryPollTimer.setInterval(3600)
		
		self._batteryBlinkTimer = QtCore.QTimer()
		self._batteryBlinkTimer.timeout.connect(lambda: (
			setattr(self, '_batteryBlink', not self._batteryBlink),
			self.updateBatteryIcon(),
		))
		self._batteryBlinkTimer.setInterval(500) #We display percentages. We update in tenth-percentage increments.
		
		self.uiBattery.clicked.connect(lambda: window.show('power'))
		
		self.uiBatteryIcon.setAttribute(Qt.WA_TransparentForMouseEvents)
		self.uiBatteryIcon.setStyleSheet('')
		api.observe('externalPower', lambda state: (
			setattr(self, '_batteryCharging', state),
			state and (
				self._batteryBlinkTimer.stop(),
				setattr(self, '_batteryBlink', False),
			),
			self.updateBatteryIcon(),
		) )
		api.observe('batteryPresent', lambda state: (
			setattr(self, '_batteryPresent', state),
			state and (
				self._batteryBlinkTimer.stop(),
				setattr(self, '_batteryBlink', False),
			),
			self.updateBatteryIcon(),
		) )
		def uiBatteryIconPaintEvent(evt, rectSize=24):
			"""Draw the little coloured square on the focus peaking button."""
			if self._batteryPresent and (self._batteryCharging or not self._batteryBlink):
				powerDownLevel = api.apiValues.get('powerOffWhenMainsLost') * self.uiPowerDownThreshold
				warningLevel = powerDownLevel + 0.15
				
				x,y,w,h = (
					1,
					1,
					self.uiBatteryIcon.width() - 2,
					self.uiBatteryIcon.height() - 1,
				)
				
				p = QPainter(self.uiBatteryIcon)
				
				#Cut out the battery outline, so the battery fill level doesn't show by
				#outside the "nub". Nextly, this was taken care of by an opaque box
				#outside the battery nub in the SVG image, but this didn't work so well
				#when the button was pressed or when themes were changed. We can't fill
				#a polygon a percentage of the way very easily, and we can't just go in
				#and muck with the SVG to achieve this either like we would in browser.
				batteryOutline = QPainterPath()
				batteryOutline.addPolygon(QPolygonF([
					QPoint(x+3,y),
					QPoint(x+3,y+2), #Left battery nub chunk.
					QPoint(x,y+2),
					QPoint(x,y+h), #Bottom
					QPoint(x+w,y+h),
					QPoint(x+w,y+2),
					QPoint(x+w-3,y+2), #Right battery nub chunk.
					QPoint(x+w-3,y),
				]))
				batteryOutline.closeSubpath() #Top of battery nub.
				p.setClipPath(batteryOutline, Qt.IntersectClip)
				
				p.setPen(QPen(QColor('transparent')))
				
				if self._batteryCharge > warningLevel or self._batteryCharging:
					p.setBrush(QBrush(QColor('#00b800')))
				else:
					p.setBrush(QBrush(QColor('#f20000')))
				p.drawRect(
					x, y + h * (1-self._batteryCharge),
					w, h * self._batteryCharge )
			type(self.uiBatteryIcon).paintEvent(self.uiBatteryIcon, evt) #Invoke the superclass to paint the battery overlay image on our new rect.
		self.uiBatteryIcon.paintEvent = uiBatteryIconPaintEvent
		
		
		#Record / stop
		self.uiRecordTemplateWithTime = self.uiRecord.text()
		self.uiRecordTemplateNoTime = self.uiRecordTemplateWithTime.split('\n')[0][2:]
		self.uiRecord.clicked.connect(self.toggleRecording)
		
		def uiRecordPaintEventRecord(evt, iconSize=24, offsetX=32):
			midpoint = self.uiRecord.geometry().size()/2 - QSize(0, self.uiRecord.touchMargins()['bottom']/2)
			p = QPainter(self.uiRecord)
			p.setPen(QPen(QColor('#000000')))
			p.setBrush(QBrush(QColor('#f20000')))
			p.setRenderHint(QPainter.Antialiasing, True)
			p.drawChord( #xy/wh
				midpoint.width()-iconSize/2-offsetX, midpoint.height()-iconSize/2,
				iconSize, iconSize,
				0, 16*360, #start, end angle
			)
		def uiRecordPaintEventPause(evt, iconSize=20, offsetX=24):
			midpoint = self.uiRecord.geometry().size()/2 - QSize(0, self.uiRecord.touchMargins()['bottom']/2)
			p = QPainter(self.uiRecord)
			p.setPen(QPen(QColor('#ffffff')))
			p.setBrush(QBrush(QColor('#000000')))
			p.drawRect( #xy/wh
				midpoint.width()-iconSize/2-offsetX, midpoint.height()-iconSize/2,
				iconSize/3, iconSize,
			)
			p.drawRect( #xy/wh
				midpoint.width()-iconSize/2-offsetX+iconSize/3*2, midpoint.height()-iconSize/2,
				iconSize/3, iconSize,
			)
		def uiRecordPaintEventStop(evt, iconSize=20, offsetX=24):
			midpoint = self.uiRecord.geometry().size()/2 - QSize(0, self.uiRecord.touchMargins()['bottom']/2)
			p = QPainter(self.uiRecord)
			p.setPen(QPen(QColor('#ffffff')))
			p.setBrush(QBrush(QColor('#000000')))
			p.drawRect( #xy/wh
				midpoint.width()-iconSize/2-offsetX, midpoint.height()-iconSize/2,
				iconSize, iconSize,
			)
			self.uiRecord.setText( #Do the timer.
				self.uiRecordTemplateWithTime.format(
					state="Stop",
					timeRecorded=(recordingEndTime or time()) - recordingStartTime,
				)
			)
		def uiRecordPaintEvent(evt):
			type(self.uiRecord).paintEvent(self.uiRecord, evt)
			#TODO DDR 2019-10-07: Add pause icon, when we are able to pause recording and resume again, for run 'n' gun mode.
			if self.uiRecord.isRecording:
				uiRecordPaintEventRecord(evt)
			else:
				uiRecordPaintEventStop(evt)
		self.uiRecord.paintEvent = uiRecordPaintEvent
		
		api.observe('state', self.onStateChange)
		
		#Play & save
		#TODO DDR 2019-09-27 fill in play and save
		uiPlayAndSaveTemplate = self.uiPlayAndSave.text()
		self.uiPlayAndSave.setText("Play && Save\n-1s RAM\n-1s Avail.")
		
		playAndSaveData = api.getSync(['cameraMaxFrames', 'frameRate', 'recSegments'])
		def updatePlayAndSaveText(*_):
			data = playAndSaveData
			segmentMaxRecTime = data['cameraMaxFrames'] / data['frameRate'] / data['recSegments']
			segmentCurrentRecTime = min(
				segmentMaxRecTime, 
				(recordingEndTime or time()) - recordingStartTime
			)
			self.uiPlayAndSave.setText(
				uiPlayAndSaveTemplate.format(
					ramUsed=segmentCurrentRecTime, ramTotal=segmentMaxRecTime ) )
		updatePlayAndSaveText()
			
		def updatePlayAndSaveDataMaxFrames(value):
			playAndSaveData['cameraMaxFrames'] = value
		api.observe_future_only('cameraMaxFrames', updatePlayAndSaveDataMaxFrames)
		api.observe_future_only('cameraMaxFrames', updatePlayAndSaveText)
		
		def updatePlayAndSaveDataFrameRate(_):
			playAndSaveData['frameRate'] = api.getSync('frameRate')
		api.observe_future_only('framePeriod', updatePlayAndSaveDataFrameRate)
		api.observe_future_only('framePeriod', updatePlayAndSaveText)
		
		def updatePlayAndSaveDataRecSegments(value):
			playAndSaveData['recSegments'] = value
		api.observe_future_only('recSegments', updatePlayAndSaveDataRecSegments)
		api.observe_future_only('recSegments', updatePlayAndSaveText)
		
		def uiPlayAndSaveDraw(evt):
			type(self.uiPlayAndSave).paintEvent(self.uiPlayAndSave, evt)
			updatePlayAndSaveText() #Gotta schedule updates like this, because using a timer clogs the event pipeline full of repaints and updates wind up being extremely slow.
		self.uiPlayAndSave.paintEvent = uiPlayAndSaveDraw
		
		self.uiPlayAndSave.clicked.connect(lambda:
			window.show('play_and_save')) #This should prompt to record if no footage is recorded, and explain itself.
		
		
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
				def updateExternalMediaTextCallback(space):
					saved = estimateFile.duration(space['used'] * 1000)
					total = estimateFile.duration(space['total'] * 1000)
					updateExternalMediaPercentFull(space['used']/space['total']),
					
					self.uiExternalMedia.setText(
						uiExternalMediaTemplate.format(
							externalStorageIdentifier = partition['name'] or f"{round(partition['size'] / 1e9):1.0f}GB Storage Media",
							percentFull = round(space['used']/space['total'] * 100),
							footageSavedDuration = '-1', #TODO: Calculate bits per second recorded and apply it here to the partition usage and total.
							hoursSaved = saved.days*24 + saved.seconds/60/60,
							minutesSaved = (saved.seconds/60) % 60,
							secondsSaved = saved.seconds % 60,
							hoursTotal = total.days*24 + total.seconds/60/60,
							minutesTotal = (total.seconds/60) % 60,
							secondsTotal = total.seconds % 60,
						)
					)
				api.externalPartitions.usageFor(partition['device'], 
					updateExternalMediaTextCallback )
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
		
		api.video.call('livedisplay', {})
		
		self.hideMenu()
	
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
	
	
	def toggleFocusPeakingColorMenu(self):
		#TODO DDR 2019-09-27: Make this work right. ie, animate, close when you tap away, etc. Basically reword animate.
		if not self.uiFocusPeakingColorMenu.isVisible():
			self.showMenu(self.uiFocusPeakingColor, self.uiFocusPeakingColorMenu)
		else:
			self.hideMenu()
	
	
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
		powerDownLevel = api.apiValues.get('powerOffWhenMainsLost') * self.uiPowerDownThreshold
		warningLevel = powerDownLevel + 0.15
		criticalLevel = powerDownLevel + 0.05
		if not charge > warningLevel and self._batteryCharge > warningLevel:
			self.blinkBatteryAFewTimes()
		if not charge > criticalLevel and self._batteryCharge > criticalLevel:
			self._batteryBlinkTimer.start()
		if charge > criticalLevel and not self._batteryCharge > criticalLevel:
			self._batteryBlinkTimer.stop(),
			setattr(self, '_batteryBlink', False),
		self._batteryCharge = charge #0..1
		
		self.uiBatteryIcon.update()
		self.uiBattery.setText(
			self._batteryTemplate.format(
				round(charge*100) ) )
	
	def blinkBatteryAFewTimes(self):
		animate.delay(self, 750*1, lambda: (setattr(self, '_batteryBlink', True),  self.updateBatteryIcon()))
		animate.delay(self, 750*2, lambda: (setattr(self, '_batteryBlink', False), self.updateBatteryIcon()))
		animate.delay(self, 750*3, lambda: (setattr(self, '_batteryBlink', True),  self.updateBatteryIcon()))
		animate.delay(self, 750*4, lambda: (setattr(self, '_batteryBlink', False), self.updateBatteryIcon()))
		animate.delay(self, 750*5, lambda: (setattr(self, '_batteryBlink', True),  self.updateBatteryIcon()))
		animate.delay(self, 750*6, lambda: (setattr(self, '_batteryBlink', False), self.updateBatteryIcon()))
		animate.delay(self, 750*7, lambda: (setattr(self, '_batteryBlink', True),  self.updateBatteryIcon()))
		animate.delay(self, 750*8, lambda: (setattr(self, '_batteryBlink', False), self.updateBatteryIcon()))
	
	def updateBatteryIcon(self):
		if not self._batteryPresent:
			iconState = 'missing'
		elif self._batteryCharging:
			iconState = 'charging'
		else:
			if self._batteryBlink: #DDR 2019-10-02: So, *several* hours later, I have determined that you can't actually blink the charging icon in synchrony with the background. _batteryBlink is an override, so we can only override to the opposite of the natural state - which is shown and hidden, respectfully. We could introduce another variable to solve this, but the effort to track the state is more trouble than it's worth for now.
				iconState = 'charging'
			else:
				iconState = 'discharging'
		
		self.uiBatteryIcon.pixmap().load(
			f"./assets/images/battery-{iconState}.svg" )
		self.uiBatteryIcon.update()
		
	
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
		self.uiRecord.isRecording = state == 'idle'
		self.uiRecord.update() #Redraw the icon, maybe start the timer.
		if self.uiRecord.isRecording:
			self.uiRecord.setText(
				self.uiRecordTemplateNoTime.format(state='Record') )
		
		if state == 'idle' and settings.value('autoSaveVideo', False): #[autosave]
			self._window.show('play_and_save')
	
	
	def startRecording(self):
		self.uiRecord.isRecording = False
		self.uiRecord.update()
		api.control.callSync('startRecording')
	
	def stopRecording(self):
		self.uiRecord.isRecording = True
		self.uiRecord.update()
		self.uiRecord.setText(
			self.uiRecordTemplateNoTime.format(state='Record') )
		api.control.callSync('stopRecording')
	
	
	def showOptionOnTap(self, pos: QtCore.QModelIndex):
		self.uiMenuScroll.model().itemData(pos)[Qt.UserRole]['open']()
		self.uiMenuScroll.selectionModel().clear()
	
	def showOptionOnJogWheelClick(self):
		self.uiMenuScroll.selectionModel().currentIndex().data(Qt.UserRole)['open']()
		self.uiMenuScroll.selectionModel().clear()
	
	def filterMenu(self):
		model = self.uiMenuScroll.model()
		search = self.uiMenuFilter.text().casefold()
		
		for row in range(model.rowCount()):
			data = model.data(model.index(row, 0), Qt.UserRole) #eg. {'name':"About Camera", 'open':lambda: window.show('about_camera'), 'synonyms':"kickstarter thanks me name"},
			searchMatches = (search in data['name'].casefold() or search in data['synonyms'])
			self.uiMenuScroll.setRowHidden(row,
				not searchMatches if search else data['hidden'])