# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtCore
from PyQt5.QtCore import pyqtSlot, QPropertyAnimation, QPoint
from PyQt5.QtWidgets import QWidget, QApplication

import time, math
from termcolor import cprint

from debugger import *; dbg

import api
import api2

import settings
from widgets.button import Button


class Main(QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/main.right-handed.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setFixedSize(800, 480) #hide menus, which are defined off-screen to the right
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Widget behavour.
		self.uiRecord.clicked.connect(self.recordPressed)
		self.uiDebugA.clicked.connect(self.makeFailingCall)
		self.uiDebugB.clicked.connect(lambda: window.show('test'))
		self.uiDebugC.setFocusPolicy(QtCore.Qt.NoFocus) #Break into debugger without loosing focus, so you can debug focus issues.
		self.uiDebugC.clicked.connect(lambda: self and window and dbg()) #"self" is needed here, won't be available otherwise.
		self.uiClose.clicked.connect(QApplication.closeAllWindows)
		
		#Only show the debug controls if enabled in factory settings.
		settings.observe('debug controls enabled', lambda show='False':
			self.uiDebugControls.hide() if show == 'False' else self.uiDebugControls.show() )
		
		
		self.uiBattery.clicked.connect(lambda: window.show('power'))
		
		self.uiPrefsAndUtils.clicked.connect(lambda: window.show('primary_settings'))
		
		
		closeRecordingAndTriggersMenu = self.linkButtonToMenu(
			self.uiRecordingAndTriggers, 
			self.uiRecordingAndTriggersMenu )
		
		self.uiRecordModes.clicked.connect(closeRecordingAndTriggersMenu)
		self.uiRecordingSettings.clicked.connect(closeRecordingAndTriggersMenu)
		self.uiTriggerDelay.clicked.connect(closeRecordingAndTriggersMenu)
		self.uiTriggerIOSettings.clicked.connect(closeRecordingAndTriggersMenu)
		
		
		closeShotAssistMenu = self.linkButtonToMenu(
			self.uiShotAssist, 
			self.uiShotAssistMenu )
		
		self.uiShotAssist.clicked.connect(closeRecordingAndTriggersMenu)
		
		self.uiShowWhiteClipping.stateChanged.connect(
			lambda state: api2.set(
				{'zebraLevel': state/2} ) )
		api2.observe('zebraLevel', self.updateWhiteClipping)
		
		api2.observe('focusPeakingLevel', self.updateFocusPeakingIntensity)
		
		self.uiFocusPeakingIntensity.currentIndexChanged.connect(
			lambda index: api2.set(
				{'focusPeakingLevel': index/(self.uiFocusPeakingIntensity.count()-1) } ) )
		
		self.uiFocusPeakingIntensity.currentIndexChanged.connect(
			self.uiShotAssistMenu.setFocus )
		
		api2.observe('focusPeakingColor', self.updateFocusPeakingColor)
		
		self.uiBlueFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'blue'} ) )
		self.uiPinkFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'magenta'} ) )
		self.uiRedFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'red'} ) )
		self.uiYellowFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'yellow'} ) )
		self.uiGreenFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'green'} ) )
		self.uiCyanFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'cyan'} ) )
		self.uiBlackFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'black'} ) )
		self.uiWhiteFocusPeaking.clicked.connect(lambda:
			api2.set({'focusPeakingColor': 'white'} ) )
		
		self.uiBlueFocusPeaking.clicked.connect(self.uiShotAssistMenu.setFocus)
		self.uiPinkFocusPeaking.clicked.connect(self.uiShotAssistMenu.setFocus)
		self.uiRedFocusPeaking.clicked.connect(self.uiShotAssistMenu.setFocus)
		self.uiYellowFocusPeaking.clicked.connect(self.uiShotAssistMenu.setFocus)
		self.uiGreenFocusPeaking.clicked.connect(self.uiShotAssistMenu.setFocus)
		self.uiCyanFocusPeaking.clicked.connect(self.uiShotAssistMenu.setFocus)
		
		
		#Twiddle the calibration menu so it shows the right thing. It's pretty context-sensitive - you can't white-balance a black-and-white camera, and you can't do motion trigger calibration when there's no motion trigger set up.
		#I think the sanest approach is to duplicate the button, one for each menu, since opening the menu is pretty complex and I don't want to try dynamically rebind menus.
		if not api.get('sensorRecordsColor'):
			self.uiCalibration = self.uiCalibrationOrBlackCal
			self.uiBlackCal0 = Button(parent=self.uiCalibrationOrBlackCal.parent())
			self.copyButton(src=self.uiCalibrationOrBlackCal, dest=self.uiBlackCal0)
			self.uiBlackCal0.setText(self.uiBlackCal1.text())
			
			self.closeCalibrationMenu = self.linkButtonToMenu(
				self.uiCalibration, 
				self.uiCalibrationMenu )
			
			self.uiCalibration.clicked.connect(self.closeShotAssistMenu)
			self.uiCalibration.clicked.connect(self.closeRecordingAndTriggersMenu)
			self.uiRecordingAndTriggers.clicked.connect(self.closeCalibrationMenu)
			self.uiShotAssist.clicked.connect(self.closeCalibrationMenu)
			
			#WB is either removed or becomes recalibrate motion trigger in this mode.
			self.uiWhiteBalance1.setText(self.uiRecalibrateMotionTrigger.text())
			self.uiWhiteBalance1.clicked.connect(self.closeCalibrationMenu)
			self.uiWhiteBalance1.clicked.connect(self.closeShotAssistMenu)
			self.uiWhiteBalance1.clicked.connect(self.closeRecordingAndTriggersMenu)
			self.uiWhiteBalance1.clicked.connect(lambda: api2.control('startAutoWhiteBalance', {}))
			
			self.uiBlackCal0.clicked.connect(self.closeCalibrationMenu)
			self.uiBlackCal0.clicked.connect(lambda: 
				api2.control('startCalibration', {'blackCal': True}) ) #may time out if already in progress - check state is 'idle' before issuing call!
			self.uiBlackCal1.clicked.connect(self.closeCalibrationMenu)
			self.uiBlackCal1.clicked.connect(lambda: 
				api2.control('startCalibration', {'blackCal': True}) )
			
			api.observe('triggerConfiguration', self.updateBaWTriggers)
		else:
			self.uiCalibration1 = self.uiCalibrationOrBlackCal
			self.uiCalibration2 = Button(parent=self.uiCalibrationOrBlackCal.parent())
			self.copyButton(src=self.uiCalibration1, dest=self.uiCalibration2)
			
			self.closeCalibrationMenu1 = self.linkButtonToMenu(
				self.uiCalibration1, 
				self.uiCalibrationMenu )
			self.closeCalibrationMenu2 = self.linkButtonToMenu(
				self.uiCalibration2, 
				self.uiCalibrationMenuWithMotion )
			
			#Calibration either opens the uiCalibrationMenu or the uiCalibrationMenuWithMotion [trigger button].
			self.uiWhiteBalance1.clicked.connect(self.closeCalibrationMenu1)
			self.uiWhiteBalance1.clicked.connect(self.closeCalibrationMenu2)
			self.uiWhiteBalance1.clicked.connect(lambda: api2.control('startAutoWhiteBalance', {}))
			self.uiWhiteBalance2.clicked.connect(self.closeCalibrationMenu1)
			self.uiWhiteBalance2.clicked.connect(self.closeCalibrationMenu2)
			self.uiWhiteBalance2.clicked.connect(lambda: api2.control('startAutoWhiteBalance', {}))
			self.uiBlackCal1.clicked.connect(self.closeCalibrationMenu1)
			self.uiBlackCal1.clicked.connect(self.closeCalibrationMenu2)
			self.uiBlackCal1.clicked.connect(lambda: api2.control('startCalibration', {'blackCal': True}))
			self.uiBlackCal2.clicked.connect(self.closeCalibrationMenu1)
			self.uiBlackCal2.clicked.connect(self.closeCalibrationMenu2)
			self.uiBlackCal2.clicked.connect(lambda: api2.control('startCalibration', {'blackCal': True}))
			self.uiRecalibrateMotionTrigger.clicked.connect(self.closeCalibrationMenu1)
			self.uiRecalibrateMotionTrigger.clicked.connect(self.closeCalibrationMenu2)
			self.uiRecalibrateMotionTrigger.clicked.connect(lambda: api.control('takeStillReferenceForMotionTriggering'))
			
			#Close other menus and vice-versa when menu opened.
			self.uiRecordingAndTriggers.clicked.connect(self.closeCalibrationMenu1)
			self.uiRecordingAndTriggers.clicked.connect(self.closeCalibrationMenu2)
			self.uiRecordingAndTriggers.clicked.connect(closeShotAssistMenu)
			self.uiShotAssist.clicked.connect(self.closeCalibrationMenu1)
			self.uiShotAssist.clicked.connect(self.closeCalibrationMenu2)
			self.uiCalibration1.clicked.connect(closeRecordingAndTriggersMenu)
			self.uiCalibration2.clicked.connect(closeRecordingAndTriggersMenu)
			self.uiCalibration1.clicked.connect(closeShotAssistMenu)
			self.uiCalibration2.clicked.connect(closeShotAssistMenu)
			
			#[TODO DDR 2018-09-13] This widget needs to support being clicked on / focussed in on, so it can close all the menus.
			#self.uiPinchToZoomGestureInterceptionPanel.clicked.connect(self.closeCalibrationMenu1)
			#self.uiPinchToZoomGestureInterceptionPanel.clicked.connect(self.closeCalibrationMenu2)
			#self.uiPinchToZoomGestureInterceptionPanel.clicked.connect(closeRecordingAndTriggersMenu)
			#self.uiPinchToZoomGestureInterceptionPanel.clicked.connect(closeShotAssistMenu)
			
			api.observe('triggerConfiguration', self.updateColorTriggers)
		
		
		self.uiRecordModes.clicked.connect(lambda: window.show('record_mode'))
		self.uiRecordingSettings.clicked.connect(lambda: window.show('recording_settings'))
		self.uiTriggerIOSettings.clicked.connect(lambda: window.show('triggers'))
		self.uiTriggerDelay.clicked.connect(lambda: window.show('trigger_delay'))
		
		self.uiPlayAndSave.clicked.connect(lambda: window.show('play_and_save'))
		
		# Polling-based updates.
		self.updateBatteryCharge()
		self._timer = QtCore.QTimer()
		self._timer.timeout.connect(self.updateBatteryCharge)
		self._timer.start(4000) #ms
		
		#Set up exposure slider.
		# This slider is significantly more responsive to mouse than to touch. 🤔
		#api2.observe('exposurePeriod', self.updateExposureNs)
		self.uiExposureSlider.setMaximum(api2.get('exposureMax')) #TODO: This is incorrect, should use update not update_future_only since we're drawing from the wrong value -_-
		self.uiExposureSlider.setMinimum(api2.get('exposureMin'))
		api2.observe_future_only('exposureMax', self.updateExposureMax)
		api2.observe_future_only('exposureMin', self.updateExposureMin)
		#[TODO DDR 2018-09-13] This valueChanged event is really quite slow, for some reason.
		self.uiExposureSlider.debounce.sliderMoved.connect(self.onExposureSliderMoved)
		self.uiExposureSlider.touchMargins = lambda: {
			"top": 10, "left": 30, "bottom": 10, "right": 30
		}
		
		#Oh god this is gonna mess up scroll wheel selection so badly. 😭
		self.uiShowWhiteClipping.stateChanged.connect(self.uiShotAssistMenu.setFocus)
		
		#Set the kerning to false because it looks way better.
		#Doesn't seem to be working? --DDR 2019-05-29
		font = self.uiResolutionOverlay.font()
		font.setKerning(False)
		self.uiResolutionOverlay.setFont(font)
		self.uiExposureOverlay.setFont(font)
	
	def onShow(self):
		videoState = api.get('videoState')
		api.set({
			'videoState':
				videoState 
				if videoState in ['pre-recording', 'recording'] else 
				'pre-recording',
			'videoDisplayDevice': 'camera',
			'videoDisplayX': self.x(),
			'videoDisplayY': self.y(),
			'videoDisplayWidth': self.width() - 200, #-200 for the sidebar. This needs to be redone a little so it calculates the position on the fly.
			'videoDisplayHeight': self.height(),
		})
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printAnalogGain(self):
		print("Analog gain is %ix." % api.get("recordingAnalogGainMultiplier"))
	
	def updateBatteryCharge(self):
		charged = f"{round(api.control('get', ['batteryCharge'])['batteryCharge']*100)}%"
		self.uiBattery.setText(charged)
	
	def onExposureSliderMoved(self, newExposureNs):
		#startTime = time.perf_counter()
		linearRatio = (newExposureNs-self.uiExposureSlider.minimum()) / (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum())
		log.print(f'lr {linearRatio}')
		api2.control.call('set', {
			'exposurePercent': math.pow(linearRatio, 2)*100,
		}).then(self.onExposureSliderMovedOk)
	def onExposureSliderMovedOk(self, response):
		log.print(f'resp {response}')
		exponentialRatio = math.sqrt(response['exposurePercent']/100)
		self.uiExposureSlider.setValue(exponentialRatio * (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum()) + self.uiExposureSlider.minimum())
	
	@pyqtSlot(int, name="updateExposureNs")
	@api2.silenceCallbacks()
	def updateExposureNs(self, newExposureNs):
		linearRatio = (newExposureNs-self.uiExposureSlider.minimum()) / (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum())
		exponentialRatio = math.sqrt(linearRatio)
		self.uiExposureSlider.setValue(exponentialRatio * (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum()) + self.uiExposureSlider.minimum())
		self.updateExposureDependancies()
	
	@pyqtSlot(int, name="updateExposureMax")
	@api2.silenceCallbacks('uiExposureSlider')
	def updateExposureMax(self, newExposureNs):
		self.uiExposureSlider.setMaximum(newExposureNs)
		self.updateExposureDependancies()
	
	@pyqtSlot(int, name="updateExposureMin")
	@api2.silenceCallbacks('uiExposureSlider')
	def updateExposureMin(self, newExposureNs):
		self.uiExposureSlider.setMinimum(newExposureNs)
		self.updateExposureDependancies()
	
	def updateExposureDependancies(self):
		"""Update exposure text to match exposure slider, and sets the slider step so clicking the gutter always moves 1%."""
		percent = api2.get('exposurePercent')
		self.uiExposureOverlay.setText(f"{round(self.uiExposureSlider.value()/1000, 2)}µs ({percent:.0f}%)")
		
		step1percent = (self.uiExposureSlider.minimum() + self.uiExposureSlider.maximum()) // 100
		self.uiExposureSlider.setSingleStep(step1percent)
		self.uiExposureSlider.setPageStep(step1percent*10)
	
	
	@pyqtSlot('QVariantMap', name="updateBaWTriggers")
	@api2.silenceCallbacks()
	def updateBaWTriggers(self, triggers):
		#	VAR IF no mocal
		#		show black cal button
		#	ELSE
		#		show cal menu button → recal motion menu
		if triggers['motion']['action'] == 'none':
			self.uiCalibration.hide()
			self.uiBlackCal0.show()
		else:
			self.uiCalibration.show()
			self.uiBlackCal0.hide()
		
		#Ensure this menu is closed, since we're about to hide the thing to close it.
		self.closeCalibrationMenu()
	
	@pyqtSlot('QVariantMap', name="updateColorTriggers")
	@api2.silenceCallbacks()
	def updateColorTriggers(self, triggers):
		#	VAR IF no mocal
		#		show cal menu button → wb/bc menu
		#	ELSE
		#		show cal menu button → wb/bc/recal menu
		if triggers['motion']['action'] == 'none':
			self.uiCalibration1.show()
			self.uiCalibration2.hide()
		else:
			self.uiCalibration1.hide()
			self.uiCalibration2.show()
	
		#Ensure this menu is closed, since we're about to hide the thing to close it.
		self.closeCalibrationMenu1()
		self.closeCalibrationMenu2()
		
	
	@pyqtSlot(float, name="updateWhiteClipping")
	@api2.silenceCallbacks('uiShowWhiteClipping')
	def updateWhiteClipping(self, focusPeakingIntensity: float):
		self.uiShowWhiteClipping.setCheckState(
			0 if not focusPeakingIntensity else 2)
	
	
	@pyqtSlot(str, name="updateFocusPeakingIntensity")
	@api2.silenceCallbacks('uiFocusPeakingIntensity')
	def updateFocusPeakingIntensity(self, focusPeakingIntensity: str):
		snapPoints = self.uiFocusPeakingIntensity.count() - 1 #zero-indexed
		threshold = 0.02
		snapPoint = round(focusPeakingIntensity*snapPoints)
		diff = abs(snapPoint - (focusPeakingIntensity*snapPoints))/snapPoints
		if diff < threshold:
			self.uiFocusPeakingIntensity.setCurrentIndex(snapPoint)
		else:
			self.uiFocusPeakingIntensity.setCurrentText(f"{focusPeakingIntensity*100:.0f}%")
	
	
	@pyqtSlot(str, name="updateFocusPeakingColor")
	@api2.silenceCallbacks() #Causes pyqtSlot to overwrite earlier function.
	def updateFocusPeakingColor(self, color: int):
		QPoint = QtCore.QPoint
		
		box = self.uiFocusPeakingColorSelectionIndicator
		boxSize = QPoint(
			box.geometry().width(),
			box.geometry().height() )
		
		
		if color == 'blue':
			origin = self.uiBlueFocusPeaking.geometry().bottomRight()
			box.move(origin - boxSize + QPoint(1,1))
		elif color == 'magenta':
			origin = self.uiPinkFocusPeaking.geometry().bottomLeft()
			box.move(origin - QPoint(0, boxSize.y()-1))
		elif color == 'red':
			origin = self.uiRedFocusPeaking.geometry().bottomRight()
			box.move(origin - boxSize + QPoint(1,1))
		elif color == 'yellow':
			origin = self.uiYellowFocusPeaking.geometry().topLeft()
			box.move(origin)
		elif color == 'green':
			origin = self.uiGreenFocusPeaking.geometry().topRight()
			box.move(origin - boxSize + QPoint(1,1))
		elif color == 'cyan':
			origin = self.uiCyanFocusPeaking.geometry().topLeft()
			box.move(origin)
		elif color == 'white':
			origin = self.uiWhiteFocusPeaking.geometry().topRight()
			box.move(origin - QPoint(boxSize.x()-1, 0))
		elif color == 'black':
			origin = self.uiBlackFocusPeaking.geometry().topLeft()
			box.move(origin)
		else:
			print('unknown focus peaking color', color)
			box.move(0,99999)
	
	
	def linkButtonToMenu(self, button, menu):
		"""Have one of the side bar buttons bring up its menu.
			
			The menu closes when it loses focus.
			
			Returns a function which can be called to hide the menu, by an external widget.
		"""
		
		paddingLeft = 20 #Can't extract this from the CSS without string parsing.
		shownAt = QPoint(self.uiPlayAndSave.x() - menu.width() + 1, menu.y())
		hiddenAt = QPoint(self.uiPlayAndSave.x() - paddingLeft, menu.y())
		anim = QPropertyAnimation(menu, b"pos")
		anim.setDuration(17) #framerate ms (?) * frames to animate, excluding start and end frame?
		anim.setStartValue(hiddenAt)
		anim.setEndValue(shownAt)
		menu.hide()
		
		def toggleMenu():
			"""Start to show the menu, or start to hide the menu if it's already opened."""
			menu.show()
				
			if anim.currentTime() == 0 or anim.direction() == QPropertyAnimation.Backward:
				anim.setDirection(QPropertyAnimation.Forward)
				menu.setFocus()
				button.keepActiveLook = True
				button.refreshStyle()
			else:
				anim.setDirection(QPropertyAnimation.Backward)
				
			if anim.state() == QPropertyAnimation.Stopped:
				anim.start()
		
		button.clicked.connect(toggleMenu)
		
		def hideMenu(*_):
			"""Start to hide the menu, if not in use."""
			if button.hasFocus():
				# The button to toggle this menu is now focused, and will
				# probably toggle it shut. Don't close the menu, or it would
				# toggle it open again.
				return
			
			if any(child.hasFocus() for child in menu.children()):
				# Don't close when a sub-element is selected. This has to be
				# taken care of manually by the sub-element, because in the
				# focus assist menu not all buttons go to other screens.
				return
			
			anim.setDirection(QPropertyAnimation.Backward)
			
			if anim.state() == QPropertyAnimation.Stopped:
				anim.start()
			
			# The original idea was animate margin left and button width, instead
			# of the menu position, so that the buttons were always fully
			# clickable even before they'd appeared. However, as it seems
			# effectively impossible to change the margin of a button without
			# going through (text-based) CSS, we just animate the whole menu. :(
			
			#child = menu.children()[0]
			#margins = child.contentsMargins() #doesn't work, probably qt bug - just returns 0,0,0,0
			#margins = child.style().subElementRect(QtWidgets.QStyle.SE_PushButtonFocusRect, QtWidgets.QStyleOptionButton(), child) #doesn't work, returns … default margins? I'm not sure what 21,21,-22,-22 is.
			#margins = ???
		
		menu.focusOutEvent = hideMenu
		
		def forceHideMenu(*_):
			"""Start to hide the menu, even if something's focussed on it."""
			anim.setDirection(QPropertyAnimation.Backward)
			if anim.state() == QPropertyAnimation.Stopped:
				anim.start()
		
		def animationFinished():
			"""Actually hide the menu when the menu hiding animation finishes."""
			if anim.direction() == QPropertyAnimation.Backward:
				menu.hide()
				button.keepActiveLook = False
				button.refreshStyle()
			
		anim.finished.connect(animationFinished)
		
		return forceHideMenu
	
	
	def copyButton(_, *, src, dest):
		dest.setText(src.text())
		dest.clickMarginTop = src.clickMarginTop
		dest.clickMarginLeft = src.clickMarginLeft
		dest.clickMarginBottom = src.clickMarginBottom
		dest.clickMarginRight = src.clickMarginRight
		dest.setGeometry(src.geometry())
		dest.customStyleSheet = src.customStyleSheet
		QWidget.setTabOrder(src, dest)
	
	def makeFailingCall(self):
		print(api.control('makeFailingCall', 1))

	lastTime = -1
	def debounceRecord(self):
		now = time.time()
		if now - self.lastTime > 0.05:
			ret = True
		else:
			ret = False
			cprint("              RECORD BUTTON BOUNCE IGNORED              ", "red", "on_white")
		self.lastTime = now
		return ret

	def recordPressed(self):
		if self.debounceRecord():
			videoState = api.get('videoState')
			if videoState == 'recording':
				api.set({'videoState': 'pre-recording'})
				self.stopRecord()
			else:
				api.set({'videoState': 'recording'})
				self.startRecord()


	def startRecord(self):
		print("startRecord")

	def stopRecord(self):
		print("stopRecord")
