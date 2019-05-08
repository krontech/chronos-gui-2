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
		
		self._callbacks = {value: [] for value in _camState}
		self._callbacks['notify'] = [] #meta, watch everything
		
		QDBusConnection.systemBus().connect(
			f"com.krontech.chronos.{'control_mock' if USE_MOCK else 'control'}", 
			f"/com/krontech/chronos/{'control_mock' if USE_MOCK else 'control'}",
			f"",
			'notify', 
			self.__newKeyValue,
		)
	
	def observe(self, key, callback):
		"""Add a function to get called when a value is updated."""
		self._callbacks[key] += [callback]
	
	def unobserve(self, key, callback):
		"""Stop a function from getting called when a value is updated."""
		raise Exception('unimplimented')
	
	@pyqtSlot('QDBusMessage')
	def __newKeyValue(self, msg):
		"""Update _camState and invoke any  registered observers."""
		newItems = msg.arguments()[0].items()
		for key, value in newItems:
			print(f'note: {key} is now {value}.')
			_camState[key] = value
			for callback in self._callbacks[key]:
				callback(value)
	
	def get(self, key):
		return _camState[key]

apiValues = APIValues()


class CallbackNotSilenced(Exception):
	"""Raised when the API is passed an unsilenced callback for an event.
	
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
			saftyCheckForSilencedWidgets=True: Indicates no API requests will be made from
				this function. This is usually false, because most callbacks *do*
				cause updates to the API, and it's really hard to detect this. A
				silenced callback does not update anything, since it should silence
				all the affected fields via the @silenceCallbacks(…) decorator.
		
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
	
	if not hasattr(callback, '_isSilencedCallback') and saftyCheckForSilencedWidgets:
		raise CallbackNotSilenced(f"{callback} must consider silencing. Decorate with @silenceCallbacks(callback_name, …).")
	
	apiValues.observe(name, callback)
	callback(apiValues.get(name))


def observe_future_only(name: str, callback: Callable[[Any], None], saftyCheckForSilencedWidgets=True) -> None:
	"""Like `observe`, but without the initial callback when observing.
	
		Useful when `observe`ing a derived value, which observe can't deal with yet.
	"""
	
	if not hasattr(callback, '_isSilencedCallback') and saftyCheckForSilencedWidgets:
		raise CallbackNotSilenced(f"{callback} must consider silencing. Decorate with @silenceCallbacks(callback_name, …).")
	
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
	
	print("Self-test: Retrieve exposure period.")
	print(f"Exposure is {get('exposurePeriod')}ns.")
	print("Control API self-test passed. Goodbye!")
	
	sys.exit(0)