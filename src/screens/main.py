from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api


class Main(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi('src/screens/main.right-handed.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDebugA.clicked.connect(self.printAnalogGain)
		self.uiDebugB.clicked.connect(
			lambda: window.show('widget_test') )
		self.uiClose.clicked.connect(QtWidgets.QApplication.closeAllWindows)
		
		# Timer for text label update.
		# self.updateBatteryStatus()
		self._timer = QtCore.QTimer()
		self._timer.timeout.connect(self.updateBatteryStatus)
		self._timer.start(500) #ms
		
		# Subscribe to API updates.
		api.observe('recordingExposureNs', self.updateExposureNs)
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printAnalogGain(self):
		print("Analog gain is %ins." % api.control('get_video_settings')["analogGain"])
	
	def updateBatteryStatus(self):
		self.uiBatteryLevel.setText(
			f"{round(api.control('get_power_status')['batteryCharge']*100)}%" )
		
	@pyqtSlot(int)
	def updateExposureNs(self, newExposureNs):
		self.uiExposureSlider.setValue(newExposureNs / (1e9/100) ) #hack in the limit from the API, replace with a proper queried constant when we have state
		#self.uiExposureOverlay.setText(f"{713.1}µs ({round(newExposureNs / (1e9/100))}%)")
		
	
	# ~Emit to signal:
	# https://doc.qt.io/qt-5/qdbusmessage.html#createSignal
	#
	# ~Subscribe to dbus signal.
	# QDBusConnection::sessionBus().connect("org.gnome.SessionManager", "/org/gnome/SessionManager/Presence", "org.gnome.SessionManager.Presence" ,"StatusChanged", this, SLOT(MySlot(uint))); 