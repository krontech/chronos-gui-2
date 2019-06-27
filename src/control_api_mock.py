# -*- coding: future_fstrings -*-

"""Mock for api.py. Allows easier development & testing of the QT interface.

	This mock is less "complete" than the C-based mock, as this mock only returns
	values sensible enough to develop the UI with. Currently the C-based mock is
	used for the camera API, and this mock is used for the control api. Note that
	this mock is still available for external programs to use via the dbus
	interface.

	Usage:
	import api
	print(api.control('get_video_settings'))

	Remarks:
	The service provider component can be extracted if interaction with the HTTP
	api is desired. While there is a more complete C-based mock, in chronos-cli, it
	is exceptionally hard to add new calls to.
	
	Any comment or call in this file should be considered a proposal. It can all be
	changed if need be.
	
	TODO:
	- Add a function to get the total amount of recording time available, in frames
		and in seconds. Update recordingSegments documentation to mention it.
"""
from __future__ import unicode_literals

import sys
import random
from typing import *
from time import sleep
from pathlib import Path

from PyQt5.QtCore import pyqtSlot, QObject, QTimer, Qt, QByteArray
from PyQt5.QtDBus import QDBusConnection, QDBusMessage, QDBusError


from debugger import *; dbg
from animate import delay

# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


class MockError(Exception):
	"""An error which has been mocked out.
		
		I can't figure out how to emit dbus errors, and I can't
		figure out how to install dbus-python in my VM."""
	
	def __init__(self, type_, message):
		super().__init__(f"{type_}: {message}")


def action(actionType: str) -> callable:
	"""Function decorator to denote what class of action function performs.
		
		Available actions are 'get', 'set', and 'pure'.
			- get: Function returns a value. Even if the same input
				is given, a different value may be returned.
			- set: Function primarily updates a value. It may return
				a status. The setting action is most important.
			- pure: Function returns a value based solely on it's
				inputs. Pure functions are cachable, for example.
		
		Example:
			@action('get')
			@property
			def availableRecordingAnalogGains(self) -> list: 
				return [{"multiplier":2**i, "dB":6*i} for i in range(0,5)]
		
		This is used by the HTTP API to decide what method, POST or GET, a
		function is accessed by. Setters are POST, getters GET, and pure
		functions can be accessd by either POST or GET, since args may need
		a POST body. (GET functions only have simple type coorecion, while
		POST has full JSON support.)"""
	
	actionTypes = {'get', 'set', 'pure'}
	if actionType not in actionTypes:
		raise ValueError(f'Action type "{actionType}" not known. Known action types are: {actionTypes}.')
	
	def setAction(fn):
		setattr(fn, '_action', actionType)
		return fn
	
	return setAction

def stringifyTypeClasses(typeClass: Any) -> str:
	"""Return a type with all classes subbed out with their names."""
	if hasattr(typeClass, '__name__'): #Basic types, int, str, etc.
		return typeClass.__name__
		
	if hasattr(typeClass, '_name'): #typing types
		return typeClass._name or 'Any' #Seems to be Unions mess it up, but I don't know how to break them.
	
	if hasattr(typeClass, '__class__'):
		return str(typeClass.__class__)
	
	raise Exception(f'Unknown typeClass {typeClass}')

def removeWhitespace(text:str):
	"""Remove all leading and trailing whitespace from each line of a string."""
	return '\n'.join(filter(lambda x:x, map(str.strip, text.split('\n'))))


########################
#	Pure Functions	#
########################


def resolutionIsValid(hOffset: int, vOffset: int, hRes: int, vRes: int):
	LUX1310_MIN_HRES = 192 #The LUX1310 is our image sensor.
	LUX1310_MAX_HRES = 1280
	LUX1310_MIN_VRES = 96
	LUX1310_MAX_VRES = 1024
	LUX1310_HRES_INCREMENT = 16
	LUX1310_VRES_INCREMENT = 2
	
	return (
		hOffset > 0 and vOffset > 0 and hRes > 0 and vRes > 0
		and hRes > LUX1310_MIN_HRES and hRes + hOffset < LUX1310_MAX_HRES
		and vRes > LUX1310_MIN_VRES and vRes + vOffset < LUX1310_MAX_VRES
		and not hRes % LUX1310_HRES_INCREMENT and not hOffset % LUX1310_HRES_INCREMENT
		and not vRes % LUX1310_VRES_INCREMENT and not vOffset % LUX1310_VRES_INCREMENT
	)


def framerateForResolution(hRes: int, vRes: int) -> int:
	if type(hRes) is not int or type(vRes) is not int:
		return print("D-BUS ERROR", QDBusError.InvalidArgs, f"framerate must be of type <class 'int'>, <class 'int'>. Got type {type(hRes)}, {type(vRes)}.")
			
	return 60*4e7/(hRes*vRes+1e6) #Mock. Total BS but feels about right at the higher resolutions.





##################################
#	Callbacks for Set Values	#
##################################


#Pending callbacks is used by state callbacks to queue long-running or multi
#arg tasks such as changeRecordingResolution. This is so a call to set which
#contains x/y/w/h of a new camera resolution only actually resets the camera
#video pipeline once. Each function which appears in the list is called only
#once, after all values have been set.
pendingCallbacks = set()


def changeRecordingResolution(state):
	if state.currentState == 'preview':
		print(f"Mock: changing recording resolution to xywh {state.previewHOffset} {state.previewVOffset} {state.previewHRes} {state.previewVRes}.")
	else:
		print(f"Mock: changing recording resolution to xywh {state.recordingHOffset} {state.recordingVOffset} {state.recordingHRes} {state.recordingVRes}.")


def notifyExposureChange(state):
	print('Mock: Exposure change callback.')
	#self.emitControlSignal('maxExposureNs', 7e8) # Example.
	#self.emitControlSignal('minExposureNs', 3e2)



#######################################
#	Mock D-Bus Interface Provider	#
#######################################

class State():
	#===============================================================================================
	# API Parameters: Camera Info Group
	@property
	def cameraApiVersion(self):
		return '0.0.0-mock'
	
	@property
	def cameraFpgaVersion(self):
		return "0.0"
	
	@property
	def cameraMemoryGB(self):
		return 7.9
	
	@property
	def cameraModel(self):
		return "CR14-1.0-MOCK"
	
	@property
	def cameraSerial(self):
		return "-00001"
	
	_description = 'mock camera'
	
	@property
	def cameraDescription(self):
		return self._description
	
	@cameraDescription.setter
	def cameraDescription(self, value):
		self._description = value
	
	_cameraIDNumber = -1
	
	@property
	def cameraIDNumber(self):
		return self._cameraIDNumber
	
	@cameraIDNumber.setter
	def cameraIDNumber(self, value):
		if not isinstance(value, int):
			raise TypeError("cameraIDNumber must be an integer")
		self._cameraIDNumber = value
	
	#===============================================================================================
	# API Parameters: Sensor Info Group
	@property
	def sensorName(self):
		return 'mock sensor'
	
	@property
	def sensorColorPattern(self):
		return "rgbg"

	@property
	def sensorBitDepth(self):
		return 12
	
	@property
	def sensorISO(self):
		return 5
	
	@property
	def sensorMaxGain(self):
		return 6
	
	@property
	def sensorVMax(self):
		return 1280

	@property
	def sensorHMax(self):
		return 720
	
	@property
	def sensorVDark(self):
		return 1 #TODO: What is this?
	
	#===============================================================================================
	# API Parameters: Exposure Group
	
	_exposurePeriod = 5
	
	@property
	def exposurePeriod(self):
		return int(self._exposurePeriod * 1000000000)
	
	@exposurePeriod.setter
	def exposurePeriod(self, value):
		self._exposurePeriod = value / 1000000000

	@property
	def exposurePercent(self):
		return 100
	
	@exposurePercent.setter
	def exposurePercent(self, value):
		pass

	@property
	def shutterAngle(self):
		return 360
	
	@shutterAngle.setter
	def shutterAngle(self, value):
		pass

	@property
	def exposureMin(self):
		return 5
	
	@property
	def exposureMax(self):
		return 10
	
	#===============================================================================================
	# API Parameters: Gain Group
	_gain = 1
	
	@property
	def currentGain(self):
		return self._gain
		
	@currentGain.setter
	def currentGain(self, value):
		self._gain = value
	
	@property
	def currentISO(self):
		return self._gain * 5

	#===============================================================================================
	# API Parameters: Camera Status Group
	
	_currentState = 'idle' #There's going to be some interaction about what's valid when, wrt this variable and API calls.
	
	@property
	def currentState(self):
		return self._currentState
	
	@property
	def state(self):
		return self._currentState

	#===============================================================================================
	# API Parameters: Recording Group
	@property
	def cameraMaxFrames(self):
		"""Maximum number of frames the camera's memory can save at the current resolution."""
		return 80000
	
	_resolution = {
		"hRes": 1280,
		"vRes": 720,
		"hOffset": 0,
		"vOffset": 0,
		"vDarkRows": 0, #TODO: What is this?
		"bitDepth": 12,
	}
	
	@property
	def resolution(self):
		"""Dictionary describing the current resolution settings."""
		return _resolution
	
	@resolution.setter
	def resolution(self, value):
		self._resolution = value
	
	@property
	def minFramePeriod(self):
		"""Minimum frame period at the current resolution settings."""
		return int(1 * 1000000000)
	
	
	_framePeriod = 2000
	
	@property
	def framePeriod(self):
		"""Time in nanoseconds to record a single frame (or minimum time for frame sync and shutter gating)."""
		return int(self._framePeriod * 1000000000)
	
	@framePeriod.setter
	def framePeriod(self, value):
		self._framePeriod = value / 1000000000
	

	@property
	def frameRate(self):
		"""Estimated recording frame rate in frames per second (reciprocal of framePeriod)."""
		return 1 / self._framePeriod
	
	@frameRate.setter
	def frameRate(self, value):
		self._framePeriod = 1 / value
	
	
	@property
	def frameCapture(self):
		return 1 #TODO: What is this?

	#===============================================================================================
	# API Parameters: Color Space Group
	
	_wbMatrix = [1,1,1]
	
	@property
	def wbMatrix(self):
		"""Array of Red, Green, and Blue gain coefficients to achieve white balance."""
		return self._wbMatrix
		
	@wbMatrix.setter
	def wbMatrix(self, value):
		self._wbMatrix = value
	
	
	_colorMatrix = [
		1,0,0,
		0,1,0,
		0,0,1,
	]
	
	@property
	def colorMatrix(self):
		"""Array of 9 floats describing the 3x3 color matrix from image sensor color space in to sRGB, stored in row-scan order."""
		return self._colorMatrix
	
	@colorMatrix.setter
	def colorMatrix(self, value):
		self._colorMatrix = value

	#===============================================================================================
	# API Parameters: IO Configuration Group
	@property
	def ioMapping(self):
		return [] #TODO: What is this?
	
	@ioMapping.setter
	def ioMapping(self, value):
		pass




state = State() #Must be instantiated for QDBusMarshaller. 🙂


class ControlAPIMock(QObject):
	"""Function calls of the camera control D-Bus API.
		
		Any function decorated by a @pyqtSlot is callable over D-Bus.
		The action decorator is used by the HTTP API, so it knows
		what caching scheme it should use."""
	
	
	def emitSignal(self, signalName: str, *args) -> None:
		"""Emit an arbitrary signal. (Use emitControlSignal for API values.)"""
		signal = QDBusMessage.createSignal('/ca/krontech/chronos/control_mock', 'ca.krontech.chronos.control_mock', signalName)
		for arg in args:
			signal << arg
		QDBusConnection.systemBus().send(signal)
	
	def emitControlSignal(self, name: str, value=None) -> None:
		"""Emit an update signal, usually for indicating a value has changed."""
		signal = QDBusMessage.createSignal('/ca/krontech/chronos/control_mock', 'ca.krontech.chronos.control_mock', 'notify')
		signal << { name: getattr(state, name) if value is None else value }
		QDBusConnection.systemBus().send(signal)
	
	def emitError(self, message: str) -> None:
		error = QDBusMessage.createError('failed', message)
		QDBusConnection.systemBus().send(error)
	
	def holdState(self, state: str, duration: int) -> None:
		"""Set the current state to something else for a little bit. Returns to 'idle'."""
		state._currentState = state
		self.emitControlSignal('currentState')
		
		def done():
			state._currentState = 'idle'
			self.emitControlSignal('currentState')
			
		timer = QTimer(self)
		timer.timeout.connect(done)
		timer.setSingleShot(True)
		timer.start(duration) #ms
	
	
	@action('get')
	@pyqtSlot('QVariantList', result='QVariantMap')
	def get(self, keys: List[str]): #Dict[str, Any]
		retval = {}
		
		for key in keys:
			if key[0] is '_' or not hasattr(state, key): # Don't allow querying of private variables.
				#QDBusMessage.createErrorReply does not exist in PyQt5, and QDBusMessage.errorReply can't be sent. As far as I can tell, we simply can not emit D-Bus errors.
				#Can't reply with a single string, either, since QVariantMap MUST be key:value pairs and we don't seem to have unions or anything.
				#The type overloading, as detailed at http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator, simply does not work in this case. The last pyqtSlot will override the first pyqtSlot with its return type.
				return MockError('ValueError', f"The value '{key}' is not a known key to set.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
			
			retval[key] = getattr(state, key)
		
		return retval
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def set(self, data: dict):
		# Check all errors first to avoid partially applying an update.
		for key, value in data.items():
			if key[0] is '_' or not hasattr(state, key):  # Don't allow setting of private variables.
				# return self.sendError('unknownValue', f"The value '{key}' is not known.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
				return MockError('ValueError', (f"The value '{key}' is not a known key to set.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}"))
			if not isinstance(value, type(getattr(state, key))):
				return MockError('ValueError', (f"Can not set '{key}', currently {getattr(state, key)}, to {value}.\nExpected {type(getattr(state, key))}, got {type(value)}."))
		
		# Set only changed variables. Changing can be quite involved, such as with recordingHRes.
		for key, value in data.items():
			if getattr(state, key) != value:
				setattr(state, key, value)
				print(f"MOCK: updated {key} to {value}")
		
		#Call each callback set. Good for multi-arg tasks such as recording resolution and trigger state.
		for cb in pendingCallbacks:
			cb(state)
		pendingCallbacks.clear()
		
		self.emitSignal('notify', data)
		
		return self.status() #¯\_(ツ)_/¯
	
	
	@action('get')
	@pyqtSlot(result="QVariantMap")
	def availableKeys(self) -> List[str]:
		"""Get a list of the properties we can get/set/subscribe.
			
			For a list of functions, see org.freedesktop.DBus.Properties.GetAll."""
		
		#Return a map, vs a list with a name key, because everything else is a{sv}.
		return {
			elem: {
				'get': True,
				'set': True,
				'notify': True, #mock, will need to be decorated with this data
			}
			for elem in dir(state)
			if elem[0] != '_' #Don't expose private items.
		}
	
	
	@action('get')
	@pyqtSlot(result="QVariantMap")
	def availableCalls(self) -> List[Dict[str, str]]:
		return {
			elem: {
				'constant': False,
				'property': False,
				'action': 'set',
			} 
			for elem in self.__class__.__dict__ 
			if hasattr(getattr(self, elem), '_action')
		}
	
	
	@action('get')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def status(self, opts):
		return {'state': state.currentState}
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def doReset(self, opts) -> None:
		print('resetting...')
		self.holdState('reinitializing', 500)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startAutoWhiteBalance(self, opts) -> None:
		print('auto white balancing...')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def revertAutoWhiteBalance(self, opts) -> None:
		print('reset white balance')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startBlackCalibration(self, opts) -> None:
		print('starting black calibration...')
		self.holdState('calibrating', 2000)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startZeroTimeBlackCal(self, opts) -> None:
		print('starting zero-time black calibration...')
		self.holdState('calibrating', 2000)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startAnalogCalibration(self, opts) -> None:
		print('starting analog calibration...')
		self.holdState('calibrating', 2000)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startRecording(self, opts) -> None:
		state._currentState = 'recording'
		self.emitControlSignal('currentState')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def getResolutionTimingLimits(self, opts) -> None:
		state._currentState = 'recording'
		self.emitControlSignal('currentState')
		return {
			"cameraMaxFrames": int(1000000),
			"minFramePeriod": int(5 * 1000000000),
			"exposureMin": int(1 * 1000000000),
			"exposureMax": int(100 * 1000000000)
		}



if not QDBusConnection.systemBus().registerService('ca.krontech.chronos.control_mock'):
	sys.stderr.write(f"Could not register control service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	raise Exception("D-Bus Setup Error")

controlAPI = ControlAPIMock() #This absolutely, positively can't be inlined or it throws error "No such object path ...". Possibly, this is because a live reference must be kept so GC doesn't eat it?
QDBusConnection.systemBus().registerObject('/ca/krontech/chronos/control_mock', controlAPI, QDBusConnection.ExportAllSlots)


#Launch the API if not imported as a library.
if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	import signal
	
	app = QCoreApplication(sys.argv)
	
	#Quit on ctrl-c.
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	print("Running coordinator api mock.")
	sys.exit(app.exec_())