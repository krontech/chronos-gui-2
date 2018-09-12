from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QPropertyAnimation, QPoint

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks
import settings
from widgets.button import Button

class Main(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/main.right-handed.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setFixedSize(800, 480) #hide menus, which are defined off-screen to the right
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Widget behavour.
		self.uiDebugA.clicked.connect(self.printAnalogGain)
		self.uiDebugB.clicked.connect(lambda: window.show('widget_test'))
		self.uiDebugC.clicked.connect(lambda: self and dbg())
		self.uiClose.clicked.connect(QtWidgets.QApplication.closeAllWindows)
		
		self.uiBattery.clicked.connect(lambda: window.show('power'))
		
		self.uiPrefsAndUtils.clicked.connect(lambda: window.show('primary_settings'))
		
		closeRecordingAndTriggersMenu = self.linkButtonToMenu(
			self.uiRecordingAndTriggers, 
			self.uiRecordingAndTriggersMenu )
		self.uiRecordModes.clicked.connect(closeRecordingAndTriggersMenu)
		self.uiRecordingSettings.clicked.connect(closeRecordingAndTriggersMenu)
		self.uiTriggerDelay.clicked.connect(closeRecordingAndTriggersMenu)
		self.uiTriggerIOSettings.clicked.connect(closeRecordingAndTriggersMenu)
		
		self.linkButtonToMenu(
			self.uiShotAssist, 
			self.uiShotAssistMenu )
		
		
		#Twiddle the calibration menu so it shows the right thing. It's pretty context-sensitive - you can't white-balance a black-and-white camera, and you can't do motion trigger calibration when there's no motion trigger set up.
		#I think the sanest approach is to duplicate the button, one for each menu, since opening the menu is pretty complex and I don't want to try dynamically rebind menus.
		if not api.get('sensorRecordsColour'):
			self.uiCalibration = self.uiCalibrationOrBlackCal
			self.uiBlackCal0 = Button(parent=self.uiCalibrationOrBlackCal.parent())
			self.copyButton(src=self.uiCalibrationOrBlackCal, dest=self.uiBlackCal0)
			self.uiBlackCal0.setText(self.uiBlackCal1.text())
			
			self.closeCalibrationMenu = self.linkButtonToMenu(
				self.uiCalibration, 
				self.uiCalibrationMenu )
			
			#WB is either removed or becomes recalibrate motion trigger in this mode.
			self.uiWhiteBalance1.setText(self.uiRecalibrateMotionTrigger.text())
			self.uiWhiteBalance1.clicked.connect(self.closeCalibrationMenu)
			self.uiBlackCal1.clicked.connect(self.closeCalibrationMenu)
			
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
			self.uiBlackCal1.clicked.connect(self.closeCalibrationMenu1)
			self.uiBlackCal1.clicked.connect(self.closeCalibrationMenu2)
			self.uiWhiteBalance2.clicked.connect(self.closeCalibrationMenu1)
			self.uiWhiteBalance2.clicked.connect(self.closeCalibrationMenu2)
			self.uiBlackCal2.clicked.connect(self.closeCalibrationMenu1)
			self.uiBlackCal2.clicked.connect(self.closeCalibrationMenu2)
			self.uiRecalibrateMotionTrigger.clicked.connect(self.closeCalibrationMenu1)
			self.uiRecalibrateMotionTrigger.clicked.connect(self.closeCalibrationMenu2)
			
			api.observe('triggerConfiguration', self.updateColourTriggers)
		
		
		self.uiRecordModes.clicked.connect(lambda: window.show('record_mode'))
		self.uiRecordingSettings.clicked.connect(lambda: window.show('recording_settings'))
		self.uiTriggerIOSettings.clicked.connect(lambda: window.show('triggers'))
		self.uiTriggerDelay.clicked.connect(lambda: window.show('trigger_delay'))
		
		self.uiPlayAndSave.clicked.connect(lambda: window.show('play_and_save'))
		
		# Polling-based updates.
		# self.updateBatteryStatus()
		self._timer = QtCore.QTimer()
		self._timer.timeout.connect(self.updateBatteryStatus)
		self._timer.start(500) #ms
		
		#Set up exposure slider.
		api.observe('recordingExposureNs', self.updateExposureNs)
		self.uiExposureSlider.setMaximum(api.get('sensorMaxExposureNs')) #TODO: This is incorrect, should use update not update_future_only since we're drawing from the wrong value -_-
		self.uiExposureSlider.setMinimum(api.get('sensorMinExposureNs'))
		api.observe_future_only('sensorMaxExposureNs', self.updateExposureMax)
		api.observe_future_only('sensorMinExposureNs', self.updateExposureMin)
		self.uiExposureSlider.valueChanged.connect(
			lambda val: api.control('set', {'recordingExposureNs': val}) )
		
		#Only show the debug controls if enabled in factory settings.
		settings.observe('debug controls enabled', lambda show='False':
			self.uiDebugControls.hide() if show == 'False' else self.uiDebugControls.show() )
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printAnalogGain(self):
		print("Analog gain is %ins." % api.get("recordingAnalogGain"))
	
	def updateBatteryStatus(self):
		charged = f"{round(api.control('get', ['batteryCharge'])['batteryCharge']*100)}%"
		self.uiBattery.setText(charged)
		
	@pyqtSlot(int)
	@silenceCallbacks('uiExposureSlider')
	def updateExposureNs(self, newExposureNs):
		self.uiExposureSlider.setValue(newExposureNs) #hack in the limit from the API, replace with a proper queried constant when we have state
		self.updateExposureDependancies()
		
	@pyqtSlot(int)
	@silenceCallbacks('uiExposureSlider')
	def updateExposureMax(self, newExposureNs):
		self.uiExposureSlider.setMaximum(newExposureNs) #hack in the limit from the API, replace with a proper queried constant when we have state
		self.updateExposureDependancies()
		
	@pyqtSlot(int)
	@silenceCallbacks('uiExposureSlider')
	def updateExposureMin(self, newExposureNs):
		self.uiExposureSlider.setValue(newExposureNs) #hack in the limit from the API, replace with a proper queried constant when we have state
		self.updateExposureDependancies()
	
	def updateExposureDependancies(self):
		"""Update exposure text to match exposure slider, and sets the slider step so clicking the gutter always moves 1%."""
		percent = round((self.uiExposureSlider.value()-self.uiExposureSlider.minimum()) / (self.uiExposureSlider.maximum()-self.uiExposureSlider.minimum()) * 99 + 1)
		self.uiExposureOverlay.setText(f"{round(self.uiExposureSlider.value()/1000, 2)}µs ({percent}%)")
		
		step1percent = (self.uiExposureSlider.minimum() + self.uiExposureSlider.maximum()) // 100
		self.uiExposureSlider.setPageStep(step1percent)
		self.uiExposureSlider.setSingleStep(step1percent)
	
	
	@pyqtSlot('QVariantMap')
	@silenceCallbacks()
	def updateBaWTriggers(self, triggers):
		#	VAR IF no mocal
		#		show black cal button
		#	ELSE
		#		show cal menu button → recal motion menu
		#dbg()
		if triggers['motion']['action'] == 'none':
			self.uiCalibration.hide()
			self.uiBlackCal0.show()
		else:
			self.uiCalibration.show()
			self.uiBlackCal0.hide()
		
		#Ensure this menu is closed, since we're about to hide the thing to close it.
		self.closeCalibrationMenu()
	
	@pyqtSlot('QVariantMap')
	@silenceCallbacks()
	def updateColourTriggers(self, triggers):
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
		dest.clickMarginTopSetter = src.clickMarginTopSetter
		dest.clickMarginLeftSetter = src.clickMarginLeftSetter
		dest.clickMarginBottomSetter = src.clickMarginBottomSetter
		dest.clickMarginRightSetter = src.clickMarginRightSetter
		dest.setGeometry(src.geometry())
		dest.customStyleSheet = src.customStyleSheet