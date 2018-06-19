"""
Mock for api.py's wrapper around control and video dbus interfaces to allow for
easier development of the QT interface.

This mock is less "complete" than the C-based mock, as this mock only returns
values sensible enough to develop the UI with. Currently the C-based mock is
used for the camera API, and this mock is used for the control api. Note that
this mock is still available for external programs to use via the dbus
interface.

Usage:
import api_mock as api
print(api.control('get_video_settings'))

Remarks:
The service provider component can be extracted if interaction with the HTTP
api is desired. While there is a more complete C-based mock, in chronos-cli, it
is exceptionally hard to add new calls to.
"""

import sys
from debugger import dbg, brk; dbg, brk

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply, QDBusMessage


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


##############################################
#    Set up mock dbus interface provider.    #
##############################################

class ControlMock(QObject):
	def __init__(self):
		super(ControlMock, self).__init__()
		self._state = {
			"recording": {
				"hres": 200,
				"vres": 300,
				"hoffset": 800,
				"voffset": 480,
				"exposureNs": 85000,
				"periodNs": 40000,
				"analogGain": 2,
			},
			
			"currentVideoState": 'viwefinder', #eg, 'viewfinder', 'playback', etc.
			"currentCameraState": 'normal', #Can also be 'saving' or 'recording'. When saving, the API is unresponsive?
			"focusPeakingColor": 0x0000ff, #currently presented as red, blue, green, alpha. - 0x000000 is off
			"focusPeakingIntensity": 0.5, #1=max, 0=off
			"zebraStripesEnabled": False,
			"connectionTime": "2018-06-19T02:05:52.664Z", #To use this, add however many seconds ago the request was made. Time should pass roughly the same for the camera as for the client.
			"disableRingBuffer": False, #In segmented mode, disable overwriting earlier recorded ring buffer segments. DDR 2018-06-19: Loial figures this was fixed, but neither of us know why it's hidden in the old UI.
			"recordedSegments": [{ #Each entry in this list a segment of recorded video. Although currently resolution/framerate is always the same, having it in this data will make it easier to fix this in the future if we do.
				"start": 0,
				"end": 1000,
				"hres": 200,
				"vres": 300,
				"timestamp": "2018-06-19T02:05:52.664Z",
			}],
			"whiteBalance": [1., 1., 1.],
			"triggerDelayNs": int(1e9),
			"triggers": {
				"trig1": {
					"action": "none",
					"threshold": 2.50,
					"invertInput": False,
					"invertOutput": False,
					"debounce": True,
					"pullup1ma": False,
					"pullup20ma": True,
				},
				"trig2": {
					"action": "none",
					"threshold": 2.75,
					"invertInput": True,
					"invertOutput": False,
					"debounce": True,
					"pullup1ma": False,
					"pullup20ma": False,
				},
				"trig3": {
					"action": "none",
					"threshold": 2.50,
					"invertInput": False,
					"invertOutput": False,
					"debounce": False,
					"pullup1ma": True,
					"pullup20ma": True,
				},
				"~a1": {
					"action": "record end",
					"threshold": 2.50,
					"invertInput": False,
					"invertOutput": False,
					"debounce": True,
					"pullup1ma": False,
					"pullup20ma": True,
				},
				"~a2": {
					"action": "none",
					"threshold": 2.50,
					"invertInput": False,
					"invertOutput": False,
					"debounce": True,
					"pullup1ma": False,
					"pullup20ma": True,
				},
			},
		}
		
	@pyqtSlot(result='QVariantMap')
	def get_camera_data(self):
		return {
			"model": "Mock Camera 1.4",
			"apiVersion": "1.0",
			"fpgaVersion": "3.14",
			"memoryGB": "16",
			"serial": "Captain Crunch",
		}	
		
	@pyqtSlot(result='QVariantMap')
	def get_video_settings(self):
		return self._state['recording']
	
	@pyqtSlot('QVariantMap')
	def set_video_settings(self, data):
		for k in ("recordingGeometry", "recordingExposureNs", "recordingPeriodNs", "analogGain"):
			self._state['recording'][k] = data[k]
	
	@pyqtSlot(result='QVariantMap')
	def get_sensor_data(self):
		return {
			"name": "acme9001",
			"hMax": 1920,
			"vMax": 1080,
			"hMin": 256,
			"vMin": 64,
			"hIncrement": 2,
			"vIncrement": 32,
			"pixelRate": 1920 * 1080 * 1000,
			"pixelFormat": "BYR2",
			"framerateMax": 1000,
			"quantizeTimingNs": 250,
			"maxExposureNs": int(1e9),
			"minExposureNs": 1000,
			"maxShutterAngle": 330,
		}
	
	@pyqtSlot(result='QVariantMap')
	def get_timing_limits(self):
		return {
			"maxPeriod": sys.maxsize,
			"minPeriod": (self._state['recordingGeometry']['hres'] * self._state['recordingGeometry']['vres'] * int(1e9)) / self.get_sensor_data()['pixelRate'],
			"minExposureNs": int(1e3),
			"maxExposureNs": int(1e9),
			"exposureDelayNs": 1000, 
			"maxShutterAngle": 330,
			"quantization": 1e9 / self.get_sensor_data()['quantizeTimingNs'], #DDR 2018-06-18: What is this? It's pulled from the C API's constraints.f_quantization value.
		}
	
	@pyqtSlot(result='QVariantMap')
	def get_trigger_data(self):
		return [{                     # internal id
			"name": "Trigger 1 (BNC)", # full name (human-readable label)
			"label": "TRIG1",          # short name (as printed on the case)
			"thresholdMinV": 0.,
			"thresholdMaxV": 7.2,
			"pullup1ma": True,
			"pullup20ma": True,
			"enabled": True,
			"outputCapable": True,
		}, {
			"name": "Trigger 2",
			"label": "TRIG2",
			"thresholdMinV": 0.,
			"thresholdMaxV": 7.2,
			"pullup1ma": False,
			"pullup20ma": True,
			"enabled": True,
			"outputCapable": True,
		}, {
			"name": "Trigger 3 (isolated)",
			"label": "TRIG3",
			"thresholdMinV": 0.,
			"thresholdMaxV": 7.2,
			"pullup1ma": False,
			"pullup20ma": False,
			"enabled": True,
			"outputCapable": False,
		}, { #DDR 2018-06-18: I don't know what the analog input settings will be like.
			"name": "Analog 1",
			"label": "~A1",
			"thresholdMinV": 0.,
			"thresholdMaxV": 7.2,
			"pullup1ma": False,
			"pullup20ma": False,
			"enabled": False,
			"outputCapable": False,
		}, {
			"name": "Analog 2",
			"label": "~A2",
			"thresholdMinV": 0.,
			"thresholdMaxV": 7.2,
			"pullup1ma": False,
			"pullup20ma": False,
			"enabled": False,
			"outputCapable": False,
		}]
	
	
	@pyqtSlot(QDBusMessage)
	def get(self, keys):
		retval = {}
		
		for key in keys:
			if key not in self._state:
				return QDBusMessage.createErrorReply('unknownValue', f"The value '{key}' is not known. Valid keys are: {self._state.keys()}")
			retval[key] = self._state[key]
		
		return retval
	
	
	@pyqtSlot('QVariantMap')
	def set(self, data):
		
		# Check all errors first to avoid partially applying an update.
		for key, value in data.items():
			if key not in self._state:
				return self.sendErrorReply('unknownValue', f"The value '{key}' is not known. Valid keys are: {self._state.keys()}")
			if not isinstance(value, type(self._state[key])):
				return QDBusMessage.createErrorReply('wrongType', f"Can not set '{key}' to {value}. (Previously {self._state[key]}.) Expected {type(self._state[key])}, got {type(value)}.")	
		
		for key, value in data.items():
			self._state[key] = value





if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control.mock'):
	sys.stderr.write(f"Could not register service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	sys.exit(2)

controlMock = ControlMock() #This absolutely, positively can't be inlined or it throws error "No such object path '/'".
QDBusConnection.systemBus().registerObject('/', controlMock, QDBusConnection.ExportAllSlots)




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


if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	app = QCoreApplication(sys.argv)
	
	print("Self-test: echo service")
	print(f"min recording period: {control('get_timing_limits')['tMinPeriod']}")
	print("Self-test passed. Python mock API is running.")
	
	sys.exit(app.exec_())