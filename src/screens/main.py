from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QPropertyAnimation, QPoint

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


class Main(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi('src/screens/main.right-handed.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setFixedSize(800, 480) #hide menus, which are defined off-screen to the right
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Widget behavour.
		self.uiDebugA.clicked.connect(self.printAnalogGain)
		self.uiDebugB.clicked.connect(lambda: window.show('widget_test'))
		self.uiDebugC.clicked.connect(lambda: window.show('stamp'))
		self.uiClose.clicked.connect(QtWidgets.QApplication.closeAllWindows)
		#self.uiTriggers.clicked.connect(lambda: window.show('triggers'))
		self.linkButtonToMenu(
			self.uiRecordingAndTriggers, 
			self.uiRecordingAndTriggersMenu )
		self.linkButtonToMenu(
			self.uiShotAssist, 
			self.uiShotAssistMenu )
		
		if api.get('sensorPixelFormat') == 'BYR2': #colour model
			self.linkButtonToMenu(
				self.uiCalibrationOrBlackCal, 
				self.uiCalibrationMenu )
		else:
			self.uiCalibrationOrBlackCal.setText(self.uiBlackCal.text())
		
		# Polling-based updates.
		# self.updateBatteryStatus()
		self._timer = QtCore.QTimer()
		self._timer.timeout.connect(self.updateBatteryStatus)
		self._timer.start(500) #ms
		
		#Set up exposure slider.
		api.observe('recordingExposureNs', self.updateExposureNs)
		self.uiExposureSlider.setMaximum(api.get('sensorMaxExposureNs'))
		self.uiExposureSlider.setMinimum(api.get('sensorMinExposureNs'))
		api.observe_future_only('sensorMaxExposureNs', self.updateExposureMax)
		api.observe_future_only('sensorMinExposureNs', self.updateExposureMin)
		self.uiExposureSlider.valueChanged.connect(
			lambda val: api.control('set', {'recordingExposureNs': val}) )
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printAnalogGain(self):
		print("Analog gain is %ins." % api.get("recordingAnalogGain"))
	
	def updateBatteryStatus(self):
		self.uiBattery.setText(
			f"{round(api.control('get', ['batteryCharge'])['batteryCharge']*100)}%" )
		
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
	
	def linkButtonToMenu(self, button, menu):
		"""Have one of the side bar buttons bring up its menu.
		
		The menu closes when it loses focus.
		"""
		
		paddingLeft = 20 #Can't extract this from the CSS without string parsing.
		shownAt = QPoint(self.uiPlayAndSave.x() - menu.width() + 1, menu.y())
		hiddenAt = QPoint(self.uiPlayAndSave.x() - paddingLeft, menu.y())
		anim = QPropertyAnimation(menu, b"pos")
		anim.setDuration(16*2) #framerate ms (?) * frames to animate, excluding start and end frame?
		anim.setStartValue(hiddenAt)
		anim.setEndValue(shownAt)
		menu.hide()
		
		def toggleMenu():
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
		
		def hideMenu(evt):
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
		
		def animationFinished():
			"""Hide menu when not needed."""
			if anim.direction() == QPropertyAnimation.Backward:
				menu.hide()
				button.keepActiveLook = False
				button.refreshStyle()
			
		anim.finished.connect(animationFinished)
		
	
	# ~Emit to signal:
	# https://doc.qt.io/qt-5/qdbusmessage.html#createSignal
	#
	# ~Subscribe to dbus signal.
	# QDBusConnection::sessionBus().connect("org.gnome.SessionManager", "/org/gnome/SessionManager/Presence", "org.gnome.SessionManager.Presence" ,"StatusChanged", this, SLOT(MySlot(uint))); 