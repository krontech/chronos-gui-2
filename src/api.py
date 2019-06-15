# -*- coding: future_fstrings -*-

"""Python client library for Chronos D-Bus API.

	This module provides a convenient wrapper around the D-Bus API,
	abstracting away some of the more verbose parts of connecting
	and commanding the camera. It wraps two interfaces, "control"
	and "video".

	Usage:
	import api
	print(api.control('get_video_settings'))
"""

import sys
from debugger import *; dbg

from os import environ

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply
from typing import Callable, Any
from collections import defaultdict

USE_MOCK = environ.get('USE_CHRONOS_API_MOCK') in ('always', 'gui')
if USE_MOCK:
	import coordinator_api_mock #importing starts the service
	import video_api_mock #[TODO DDR 2019-03-04]: launch this separately using systemd service units or whatever
else:
	import coordinator_api
	import video_api_mock



# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	raise Exception("D-Bus Setup Error")

cameraControlAPI = QDBusInterface(
	f"ca.krontech.chronos.{'coordinator_mock' if USE_MOCK else 'coordinator'}", #Service
	f"/ca/krontech/chronos/{'coordinator_mock' if USE_MOCK else 'coordinator'}", #Path
	f"", #Interface
	QDBusConnection.systemBus() )
cameraVideoAPI = QDBusInterface(
	f"ca.krontech.chronos.{'video_mock' if USE_MOCK else 'video_mock'}", #Service
	f"/ca/krontech/chronos/{'video_mock' if USE_MOCK else 'video_mock'}", #Path
	f"", #Interface
	QDBusConnection.systemBus() )

cameraControlAPI.setTimeout(32) #Default is -1, which means 25000ms. 25 seconds is too long to go without some sort of feedback, and the only real long-running operation we have - saving - can take upwards of 5 minutes. Instead of setting the timeout to half an hour, we should probably use events which are emitted as the event progresses. One frame (at 60fps) should be plenty of time for the API to respond, and also quick enough that we'll notice any slowness. The mock *generally* replies to messages in under 1ms, so I'm not too worried here.
cameraVideoAPI.setTimeout(32)

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
	
	def __init__(self, name, message):
		super().__init__(name)
		
		assert name, "assertion name missing"
		assert type(name) is str, f"name not str, got {name}"
		self.name = name
		
		assert message, "assertion message missing"
		assert type(message) is str, f"message not str, got {message}"
		self.message = message

class ControlReply():
	def __init__(self, value=None, errorName=None, message=None):
		self.value = value
		self.message = message
		self.errorName = errorName
	
	def unwrap(self):
		if self.errorName:
			raise APIException(self.errorName, self.message)
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
	return ControlReply(**msg.value() or {}).unwrap()


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
_camState = control('get', control('availableKeys'))
if(not _camState):
	raise Exception("Cache failed to populate. This indicates the get call is not working.")

class APIValues(QObject):
	"""Wrapper class for subscribing to API values in the chronos API."""
	
	def __init__(self):
		super(APIValues, self).__init__()
		
		#The .connect call freezes if we don't do this, or if we do this twice.
		QDBusConnection.systemBus().registerObject(
			f"/ca/krontech/chronos/{'control_mock_hack' if USE_MOCK else 'control_hack'}", 
			self,
		)
		
		self._callbacks = {}
		
		for key in _camState.keys():
			QDBusConnection.systemBus().connect(
				f"ca.krontech.chronos.{'coordinator_mock' if USE_MOCK else 'coordinator'}", 
				f"/ca/krontech/chronos/{'coordinator_mock' if USE_MOCK else 'coordinator'}",
				f"",
				key, 
				self.__newKeyValue,
			)
			self._callbacks[key] = []
		
		
		
		QDBusConnection.systemBus().connect(
			f"ca.krontech.chronos.{'coordinator_mock' if USE_MOCK else 'coordinator'}", 
			f"/ca/krontech/chronos/{'coordinator_mock' if USE_MOCK else 'coordinator'}",
			f"",
			'xvideoState', 
			self.__pvs,
		)
		QDBusConnection.systemBus().connect(
			f"ca.krontech.chronos.{'coordinator_mock' if USE_MOCK else 'coordinator'}", 
			f"/ca/krontech/chronos/{'coordinator_mock' if USE_MOCK else 'coordinator'}",
			f"",
			'xregionSaving', 
			self.__prs,
		)
		
	@pyqtSlot('QDBusMessage')
	def __pvs(self, msg):
		"""Update _camState and invoke any  registered observers."""
		print('got videoState', msg.member(), *msg.arguments())
	
	@pyqtSlot('QDBusMessage')
	def __prs(self, msg):
		"""Update _camState and invoke any  registered observers."""
		print('got regionSaving', msg.member(), *msg.arguments())
		
	
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
	
	
	#This doesn't really belong here but QTDbus is hella-finnicky and I can't be
	#bothered to figure out how to make it work elsewhere. See the __init__
	#function for details.
	signalHandlers = defaultdict(list)
	
	def connectSignal(self, signal: str, handler: Callable[[Any], None]) -> None:
		"""Wrapper class for subscribing to API signals, in the chronos API.
			
			Use observe() for api value update. Use connectSignal for
			other signals. Observe is cached, and will not pass through
			arbitrary signals.
			
			Basically, what this does is proxy each signal handler through
			the current object, which for god knows what reason (fixed in
			5.11) is the only QObject that doesn't deadlock because it's
			registered with the hack in __init__."""
		
		if not self.signalHandlers[signal]:
			QDBusConnection.systemBus().connect(
				f"ca.krontech.chronos.{'coordinator_mock' if USE_MOCK else 'coordinator'}", 
				f"/ca/krontech/chronos/{'coordinator_mock' if USE_MOCK else 'coordinator'}",
				f"",
				signal, 
				self.__connectSignalHandler,
			)
		
		self.signalHandlers[signal].append(handler)
	
	@pyqtSlot('QDBusMessage')
	def __connectSignalHandler(self, msg):
		"""Update _camState and invoke any  registered observers."""
		for handler in self.signalHandlers[msg.member()]:
			handler(*msg.arguments())

apiValues = APIValues()



class CallbackNotSilenced(Exception):
	"""Raised when the API is passed an unsilenced callback for an event.
		
		NOTE: Obsoleted by API2. Ignored now, kept only for backwards compat.
	
		It's important to silence events (with `@silenceCallbacks`) on Qt elements
		because they'll update the API with their changes otherwise. If more than
		one value is being processed by the API at the same time, it can cause an
		infinite loop where each value changes the element and the element emits
		another change event.
		
		This is explicitly checked because having an unsilenced element emit an
		update will usually work. The update will (asychronously) wind its way
		through the system, and when it gets back to updating the emitting element
		the element will have the same value and will not emit another update.
		However, if the element has a different value, then it will change back.
		The update for the change will be in flight by this time, and the two will
		enter an infinite loop of updating the element as they fight. Any further
		changes made to the element will now emit more update events which will
		themselves loop. Since this is very hard to detect reliably in testing,
		we force at least the consideration of silencing elements on the callback,
		since it makes it much easier to track down an issue by reading the
		callback and making sure it silences the elements it changes. We can't
		reasonably test if it silences the right elements unfortunately. This
		could be solved by not emitting events to the client which initiated them,
		but while fairly trivial with the socket.io websocket library, it seems
		very difficult or impossible with d-bus.
		
		Note: It is helpful to have events propagate back to the python UI
		however. It means we can ignore updating other elements when changing
		one element, since - as either element could be updated at any time
		from (say) a web ui, it doesn't really matter where the update originates
		from. All that matters is that it does update.
	"""


def observe(name: str, callback: Callable[[Any], None], saftyCheckForSilencedWidgets=True) -> None:
	"""Observe changes in a state value.
	
		Args:
			name: ID of the state variable. "exposure", "focusPeakingColor", etc.
			callback: Function called when the state updates and upon subscription.
				Called with one parameter, the new value. Called when registered
				and when the value updates.
		
		Note: Some frequently updated values (> 10/sec) are only available via
			polling due to flooding concerns. They can not be observed, as they're
			assumed to *always* be changed. See the API docs for more details.
		
		
		Rationale:
		It is convenient and less error-prone if we only have one callback that
		handles the initialization and update of values. The API provides separate
		initialization and update methods, so we'll store the initialization and
		use it to perform the initial call to the observe() callback.
		
		In addition, this means we only have to query the initial state once,
		retrieving a blob of all the data available, rather than retrieving each
		key one syscall at a time as we instantiate each Qt control.
	"""
	
	callback(apiValues.get(name))
	apiValues.observe(name, callback)


def observe_future_only(name: str, callback: Callable[[Any], None], saftyCheckForSilencedWidgets=True) -> None:
	"""Like `observe`, but without the initial callback when observing.
	
		Useful when `observe`ing a derived value, which observe can't deal with yet.
	"""
	
	apiValues.observe(name, callback)



def silenceCallbacks(*elements):
	"""Silence events for the duration of a callback.
	
		This allows an API element to be updated without triggering the API again.
		If the API was triggered, it might update the element which would cause an
		infinite loop.
	"""
	
	def silenceCallbacksOf(callback):
		def silencedCallback(self, *args, **kwargs):
			for element in elements:
				getattr(self, element).blockSignals(True)
			
			callback(self, *args, **kwargs)
			
			for element in elements:
				getattr(self, element).blockSignals(False)
		
		silencedCallback._isSilencedCallback = True #Checked by the API, which only takes silenced callbacks to avoid loops.
		return silencedCallback
	return silenceCallbacksOf


def connectSignal(*args):
	apiValues.connectSignal(*args)


#Test this component if launched on it's own.
if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	import signal
	
	app = QCoreApplication(sys.argv)
	
	#Quit on ctrl-c.
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	print("Self-test: Retrieve battery charge.")
	print(f"Battery charge: {get('batteryCharge')}")
	print("Self-test passed. Python API is up and running!")
	
	sys.exit(0)