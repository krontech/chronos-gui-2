"""
Wrapper around qt's dbus interface providing, primarily, error checking.

Usage:
import api
print(api.control('get_video_settings'))
"""

import sys
from debugger import dbg, brk; dbg, brk

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply
from typing import Callable, Any




# Set up d-bus interface. Connect to system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


cameraControlAPI = QDBusInterface(
	'com.krontech.chronos.control', #Service
	'/com/krontech/chronos/control', #Path
	'com.krontech.chronos.control', #Interface
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





# State for observe().
_camState = control('get', [
	"recording",
	"recordingExposureNs",
	"recordingPeriodNs",
	"currentVideoState",
	"currentCameraState",
	"focusPeakingColor",
	"focusPeakingIntensity",
	"zebraStripesEnabled",
	"connectionTime",
	"disableRingBuffer",
	"recordedSegments",
	"whiteBalance",
	"triggerDelayNs",
	"triggers",
])

# Keep observe()'s state up-to-date.
# TODO DDR 2018-06-22: This is broken currently, as connect() never returns here.
# We're going to ignore the fact that this doesn't work for now, as it will only matter if we reinitialize something in the camApp from this cache. 😒
__wrappers = [] #Keep a reference to the wrapper objects around. Might be needed so they don't get GC'd.
for key in _camState.keys():
	class Wrapper(QObject):
		def __init__(self):
			super(Wrapper, self).__init__()
			
			return # DDR 2018-06-22: The following function never returns, so everything is broken.
			QDBusConnection.systemBus().connect('com.krontech.chronos.control.mock', '/', '',
				key, self.updateKey)
		
		@pyqtSlot('QDBusMessage')
		def updateKey(self, msg):
			_camState[key] = msg.arguments()[0]
			
	__wrappers += [Wrapper()]


def observe(name: str, callback: Callable[[Any], None]) -> None:
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
	
	
	Allegory:
	A man asked D-Bus API what was new. After some time, D-Bus replied, "a bird
	has flown by". The man, nonplussed, thanked D-Bus and went on his way.
	
	Another man, knowing D-Bus's reputation for being literal, asked api.py
	what was new. api.py immediately responded that someone was giving away
	money in the town square! (api.py remembered D-Bus had said this earlier.)
	Quickly, the man hurried down to the square and was greatly enrinched. Some
	time later, a bird flew by.
	
	This is why we wrote this shim. We do not want to always remember to ask
	D-Bus what has happened AND what will happen. Sometimes we will forget and
	it will be hard to track down.
	"""
	
	callback(_camState[name])
	QDBusConnection.systemBus().connect('com.krontech.chronos.control.mock', '/', '',
		name, callback)




# Only export the functions we will use. Keep it simple. (This can be complicated later as the need arises.)
__all__ = ['control', 'video', 'observe'] #This doesn't work. Why?


if __name__ == '__main__':
	print("Self-test: Retrieving camera exposure.")
	print("exposure is %ins" % control('get_video_settings')["exposureNsec"])
	print("Self-test passed. Have a nice day.")