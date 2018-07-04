from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api_mock as api


class Main(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/cammainwindow.ui', self) #Maybe load f"src/screens/{self.__module__}.ui" in the future? Right now, it is clearer to load the files as named by the original camApp because we will need to reference them in both places.
		
		self.battery = {
			"charge": 0.,
			"voltage": 0.,
		}
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.cmdDebugWnd.clicked.connect(self.printAnalogGain)
		self.cmdClose.clicked.connect(QtWidgets.QApplication.closeAllWindows)
		self.cmdRecSettings.clicked.connect(lambda: window.show('recording settings'))
		self.cmdIOSettings.clicked.connect(lambda: window.show('trigger settings'))
		self.cmdUtil.clicked.connect(lambda: window.show('settings'))
		
		# Timer for text label update.
		self._timer = QtCore.QTimer()
		self._timer.timeout.connect(self.updateBatteryStatus)
		self._timer.start(500) #ms
		
		# Subscribe to API updates.
		api.observe('recordingExposureNs', self.updateExposureNs)
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printAnalogGain(self):
		print("Analog gain is %ins." % api.control('get_video_settings')["analogGain"])
	
	def updateBatteryStatus(self):
		powerStatus = api.control('get_power_status')
		self.battery["charge"] = powerStatus["batteryCharge"]
		self.battery["voltage"] = powerStatus["batteryVoltage"]
		self.updateStatusPane()
	
	def updateStatusPane(self):
		self.lblCurrent.setText("\n".join([
			f"Batt {round(self.battery['charge']*100)}% {'{:.2f}'.format(round(self.battery['voltage'], 2))}V",
			f"1280×720 1502.88fps",
			f"Exp 660.6µs (100%)",
		]))
		
	@pyqtSlot(int)
	def updateExposureNs(self, newExposureNs):
		self.expSlider.setValue(newExposureNs / (1e9/100) ) #hack in the limit from the API, replace with a proper queried constant when we have state
		
	
	# ~Emit to signal:
	# https://doc.qt.io/qt-5/qdbusmessage.html#createSignal
	#
	# ~Subscribe to dbus signal.
	# QDBusConnection::sessionBus().connect("org.gnome.SessionManager", "/org/gnome/SessionManager/Presence", "org.gnome.SessionManager.Presence" ,"StatusChanged", this, SLOT(MySlot(uint))); 