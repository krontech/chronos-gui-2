# -*- coding: future_fstrings -*-

"""Minimal dbus lock error reproduction."""

import sys
from debugger import *; dbg

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply

from control_api_mock import ControlAPIMock as ControlAPI

# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	raise Exception("D-Bus Setup Error")

if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control.mock'):
	sys.stderr.write(f"Could not register control service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	raise Exception("D-Bus Setup Error")

controlAPI = ControlAPI() #This absolutely, positively can't be inlined or it throws error "No such object path '/'". Possibly, this is because a live reference must be kept so GC doesn't eat it?
QDBusConnection.systemBus().registerObject('/com/krontech/chronos/control/mock', controlAPI, QDBusConnection.ExportAllSlots)



#####################################
#    Mock D-Bus Interface Client    #
#####################################


cameraControlAPI = QDBusInterface(
	'com.krontech.chronos.control.mock', #Service
	'/com/krontech/chronos/control/mock', #Path
	'', #Interface
	QDBusConnection.systemBus() )
cameraControlAPI.setTimeout(16) #Default is -1, which means 25000ms.
if not cameraControlAPI.isValid():
	raise Exception("D-Bus Setup Error")


def get(keyOrKeys):
	"""Call the camera control DBus get method."""
	
	keyList = [keyOrKeys] if isinstance(keyOrKeys, str) else keyOrKeys
	
	msg = QDBusReply(cameraControlAPI.call('get', keyList))
	if not msg.isValid():
		raise Exception("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()[keyOrKeys] if isinstance(keyOrKeys, str) else msg.value()


class Wrapper(QObject):
	@pyqtSlot('QDBusMessage')
	def printCharge(self, charge):
		print('new charge:', charge)



#Launch the API if not imported as a library.
if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	import signal
	
	app = QCoreApplication(sys.argv)
	
	#Quit on ctrl-c.
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	wrapper = Wrapper()
	
	print("Self-test: Retrieve battery charge.")
	print(f"Battery charge: {get('batteryCharge')}")
	
	#ERROR: This function call does not return in QT < 5.11.0
	QDBusConnection.systemBus().connect('com.krontech.chronos.control.mock', '/', '',
				'batteryCharge', wrapper.printCharge)
	
	print("Self-test passed. Python API is up and running!")
	
	sys.exit(app.exec_())