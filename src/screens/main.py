from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

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
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Widget behavour.
		self.uiDebugA.clicked.connect(self.printAnalogGain)
		self.uiDebugB.clicked.connect(lambda: window.show('widget_test'))
		self.uiClose.clicked.connect(QtWidgets.QApplication.closeAllWindows)
		self.uiTriggers.clicked.connect(lambda: window.show('triggers'))
		
		# Polling-based updates.
		# self.updateBatteryStatus()
		self._timer = QtCore.QTimer()
		self._timer.timeout.connect(self.updateBatteryStatus)
		self._timer.start(500) #ms
		
		#Set up exposure slider.
		self._timingLimits = api.control('get_timing_limits')
		self.uiExposureSlider.setMaximum(self._timingLimits['maxExposureNs'])
		self.uiExposureSlider.setMinimum(self._timingLimits['minExposureNs'])
		api.observe('recordingExposureNs', self.updateExposureNs)
		api.observe_future_only('minExposureNs', self.updateExposureMin)
		api.observe_future_only('maxExposureNs', self.updateExposureMax)
		self.uiExposureSlider.valueChanged.connect(
			lambda val: api.control('set', {'recordingExposureNs': val}) )
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printAnalogGain(self):
		print("Analog gain is %ins." % api.control('get', ["analogGain"])["analogGain"])
	
	def updateBatteryStatus(self):
		self.uiBatteryLevel.setText(
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
		
	
	# ~Emit to signal:
	# https://doc.qt.io/qt-5/qdbusmessage.html#createSignal
	#
	# ~Subscribe to dbus signal.
	# QDBusConnection::sessionBus().connect("org.gnome.SessionManager", "/org/gnome/SessionManager/Presence", "org.gnome.SessionManager.Presence" ,"StatusChanged", this, SLOT(MySlot(uint))); 