# -*- coding: future_fstrings -*-

"""Interface for the control api d-bus service."""

import sys
from debugger import *; dbg

from os import environ

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply
from typing import Callable, Any


#Mock out the old API; use production for this one so we can switch over piecemeal.
USE_MOCK = False #environ.get('USE_CHRONOS_API_MOCK') in ('always', 'web')


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	raise Exception("D-Bus Setup Error")

cameraControlAPI = QDBusInterface(
	f"com.krontech.chronos.{'control_mock' if USE_MOCK else 'control'}", #Service
	f"/com/krontech/chronos/{'control_mock' if USE_MOCK else 'control'}", #Path
	f"", #Interface
	QDBusConnection.systemBus() )
cameraVideoAPI = QDBusInterface(
	f"com.krontech.chronos.{'video_mock' if USE_MOCK else 'video'}", #Service
	f"/com/krontech/chronos/{'video_mock' if USE_MOCK else 'video'}", #Path
	f"", #Interface
	QDBusConnection.systemBus() )

cameraControlAPI.setTimeout(256) #Default is -1, which means 25000ms. 25 seconds is too long to go without some sort of feedback, and the only real long-running operation we have - saving - can take upwards of 5 minutes. Instead of setting the timeout to half an hour, we should probably use events which are emitted as the event progresses. One frame (at 60fps) should be plenty of time for the API to respond, and also quick enough that we'll notice any slowness. The mock *generally* replies to messages in under 1ms, so I'm not too worried here. The API occasionally times out after 32ms, add more time. Ugh.
cameraVideoAPI.setTimeout(256)

if not cameraControlAPI.isValid():
	print("Error: Can not connect to control D-Bus API at %s. (%s: %s)" % (
		cameraControlAPI.service(), 
		cameraControlAPI.lastError().name(), 
		cameraControlAPI.lastError().message(),
	), file=sys.stderr)
	raise Exception("D-Bus Setup Error")
if not cameraVideoAPI.isValid():
	print("Error: Can not connect to video D-Bus API at %s. (%s: %s)" % (
		cameraVideoAPI.service(), 
		cameraVideoAPI.lastError().name(), 
		cameraVideoAPI.lastError().message(),
	), file=sys.stderr)
	raise Exception("D-Bus Setup Error")



class DBusException(Exception):
	"""Raised when something goes wrong with dbus. Message comes from dbus' msg.error().message()."""
	pass

class APIException(Exception):
	"""Raised when something goes wrong with dbus. Message comes from dbus' msg.error().message()."""
	pass

class ControlReply():
	def __init__(self, value=None, errorName=None, message=None):
		self.value = value
		self.message = message
		self.errorName = errorName
	
	def unwrap(self):
		if self.errorName:
			raise APIException(self.errorName + ': ' + self.message)
		else:
			return self.value


def video(*args, **kwargs):
	"""Call the camera video DBus API. First arg is the function name.
	
		See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
		See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
		See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
	"""
	
	msg = QDBusReply(cameraVideoAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	
	return msg.value()


def control(*args, **kwargs):
	"""Call the camera control DBus API. First arg is the function name.
	
		See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
		See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
		See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
	"""
	
	#Unwrap D-Bus errors from message.
	msg = QDBusReply(cameraControlAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	
	#Unwrap API errors from message.
	return msg.value()


def get(keyOrKeys):
	"""Call the camera control DBus get method.
	
		Convenience method for `control('get', [value])[0]`.
		
		Accepts key or [key, …], where keys are strings.
		
		Returns value or {key:value, …}, respectively.
		
		See control's `availableKeys` for a list of valid inputs.
	"""
	
	valueList = control('get', 
		[keyOrKeys] if isinstance(keyOrKeys, str) else keyOrKeys )
	return valueList[keyOrKeys] if isinstance(keyOrKeys, str) else valueList


def set(values):
	"""Call the camera control DBus set method. Accepts {str: value}."""
	control('set', values)





# State cache for observe(), so it doesn't have to query the status of a variable on each subscription.
_camState = control('get', [k for k in control('availableKeys') if k not in {'dateTime'}])
if(not _camState):
	raise Exception("Cache failed to populate. This indicates the get call is not working.")

class APIValues(QObject):
	"""Wrapper class for subscribing to API values in the chronos API."""
	
	def __init__(self):
		super(APIValues, self).__init__()
		
		#The .connect call freezes if we don't do this, or if we do this twice.
		QDBusConnection.systemBus().registerObject(
			f"/com/krontech/chronos/{'control_mock_hack' if USE_MOCK else 'control_hack'}", 
			self,
		)
		
		self._callbacks = {}
		
		QDBusConnection.systemBus().connect(
			f"com.krontech.chronos.{'control_mock' if USE_MOCK else 'control'}", 
			f"/com/krontech/chronos/{'control_mock' if USE_MOCK else 'control'}",
			f"",
			'notify', 
			self.__newKeyValue,
		)
		self._callbacks['notify'] = []
	
	def observe(self, key, callback):
		"""Add a function to get called when a value is updated."""
		self._callbacks[key] += [callback]
	
	def unobserve(self, key, callback):
		"""Stop a function from getting called when a value is updated."""
		raise Exception('unimplimented')
	
	@pyqtSlot('QDBusMessage')
	def __newKeyValue(self, msg):
		"""Update _camState and invoke any  registered observers."""
		_camState[msg.member()] = msg.arguments()[0]
		for callback in self._callbacks[msg.member()]:
			callback(msg.arguments()[0])
	
	def get(self, key):
		return _camState[key]

apiValues = APIValues()


def observe(name: str, callback: Callable[[Any], None]) -> None:
	apiValues.observe(name, callback)
	



#Test this component if launched on it's own.
if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	import signal
	
	app = QCoreApplication(sys.argv)
	
	#Quit on ctrl-c.
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	print("Self-test: Retrieve battery charge.")
	print(f"Battery charge: {get('batteryCharge')}")
	print("Control API self-test passed.")
	
	sys.exit(0)