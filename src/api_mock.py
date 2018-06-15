"""
Mock for api.py's wrapper around control and video dbus interfaces to allow for
easier development of the QT interface.

Remarks:
The service provider component can be extracted if interaction with the HTTP
api is desired. While there is a C-based mock, in chronos-cli, it is
exceptionally hard to add new calls to it.

Usage:
import api_mock as api
print(api.control('get_video_settings'))
"""

import sys
from debugger import dbg, brk; dbg, brk

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


##############################################
#    Set up mock dbus interface provider.    #
##############################################

class Pong(QObject):
	@pyqtSlot(str, result=str)
	def ping(self, arg):
		print(f'ping received {arg}')
		return 'pong'


if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control.mock'):
	sys.stderr.write("Could not register service: %s\n" % QDBusConnection.systemBus().lastError().message())
	sys.exit(2)

pong = Pong() #This absolutely, positively can't be inlined or it throws error "No such object path '/'".
QDBusConnection.systemBus().registerObject('/', pong, QDBusConnection.ExportAllSlots)




#######################
#    Use the mock.    #
#######################

cameraControlAPI = QDBusInterface(
	'com.krontech.chronos.control.mock', #Service
	'/', #Path
	'', #Interface
	QDBusConnection.systemBus() )
cameraVideoAPI = QDBusInterface(
	'com.krontech.chronos.video', #Service
	'/com/krontech/chronos/video', #Path
	'com.krontech.chronos.video', #Interface
	QDBusConnection.systemBus() )

cameraControlAPI.setTimeout(16) #Default is -1, which means 25000ms. 25 seconds is too long to go without some sort of feedback, and the only real long-running operation we have - saving - can take upwards of 5 minutes. Instead of setting the timeout to half an hour, we should probably use events which are emitted as the event progresses. One frame (at 60fps) should be plenty of time for the API to respond, and also quick enough that we'll notice any slowness. The mock replies to messages in under 1ms, so I'm not too worried here.
cameraVideoAPI.setTimeout(16)

if not cameraControlAPI.isValid():
	print("Error: Can not connect to Camera D-Bus API at %s. (%s: %s)" % (
		cameraControlAPI.service(), 
		cameraControlAPI.lastError().name(), 
		cameraControlAPI.lastError().message(),
	), file=sys.stderr)
	sys.exit(-2)
if not cameraVideoAPI.isValid():
	print("Error: Can not connect to Camera D-Bus API at %s. (%s: %s)" % (
		cameraVideoAPI.service(), 
		cameraVideoAPI.lastError().name(), 
		cameraVideoAPI.lastError().message(),
	), file=sys.stderr)
	sys.exit(-2)


class DBusException(Exception):
	"""Raised when something goes wrong with dbus. Message comes from dbus' msg.error().message()."""
	pass


def control(*args, **kwargs):
	"""
	Call the camera control DBus API. First arg is the function name.
	
	See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
	See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
	See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
	"""
	
	msg = QDBusReply(cameraControlAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()


def video(*args, **kwargs):
	"""
	Call the camera video DBus API. First arg is the function name.
	
	See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
	See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
	See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
	"""
	msg = QDBusReply(cameraVideoAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()


# Only export the functions we will use. Keep it simple. (This can be complicated later as the need arises.)
__all__ = [control, video]


if True or __name__ == '__main__':
	print("Self-test: Retrieving mock camera exposure.")
	print(f"sent ping got {control('ping', 'test str')}")
	print("Self-test passed. Have a nice day.")