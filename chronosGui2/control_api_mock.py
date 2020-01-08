# -*- coding: future_fstrings -*-

"""Mock for api.py. Allows easier development & testing of the QT interface.

	This mock is less "complete" than the C-based mock, as this mock only returns
	values sensible enough to develop the UI with. Currently the C-based mock is
	used for the camera API, and this mock is used for the control api. Note that
	this mock is still available for external programs to use via the dbus
	interface.

	Usage:
	import chronosGui2.api as api
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
import datetime

from PyQt5.QtCore import pyqtSlot, QObject, QTimer
from PyQt5.QtDBus import QDBusConnection, QDBusMessage, QDBusError


from chronosGui2.debugger import *; dbg

# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


class MockError(Dict):
	"""An error which has been mocked out.
		
		I can't figure out how to emit dbus errors, and I can't
		figure out how to install dbus-python in my VM."""
	
	def __init__(self, type_, message):
		super().__init__({"error": f"{type_}: {message}"})


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
	if state._state == 'preview':
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
	def __propChange(self, propName):
		#TODO DDR 2019-12-09: Make this emit update signals like the real API? Or does our setter already cover it?
		pass
	
	#===============================================================================================
	# API Parameters: Configuration Dictionary
	@property
	def config(self):
		"""Return a configuration dictionary of all saveable parameters"""
		logging.debug('Config getter called')
		result = {}
		for name in dir(type(self)):
			if name == 'config':
				continue #Don't recurse to death looking up ourself.
			try:
				prop = getattr(type(self), name, None)
				if (isinstance(prop, property)):
					result[name] = getattr(self, name)
			except AttributeError:
				logging.error('AttributeError while accessing: %s', name)
		return result
	
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
		return "TX21-1.0-MOCK"
	
	@property
	def cameraSerial(self):
		return "-1"
	
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
		self.__propChange("cameraIdNumber")
	
	__tallyMode = 'auto'
	@property
	def cameraTallyMode(self):
		"""str: Mode in which the recording LEDs should operate.
		
		Args:
			'on': All recording LEDs on the camera are turned on.
			'off': All recording LEDs on the camera are turned off.
			'auto': The recording LEDs on the camera are on whenever the `status` property is equal to 'recording'.
		"""
		return self.__tallyMode
	@cameraTallyMode.setter
	def cameraTallyMode(self, value):
		# Update the LEDs and tally state.
		if (value == 'on'):
			pass
		elif (value == 'off'):
			pass
		elif (value == 'auto'):
			pass
		else:
			raise ValueError("cameraTallyMode value of '%s' is not supported" % (value))

		self.__tallyMode = value
		self.__propChange('cameraTallyMode')
	
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
	def sensorMaxGain(self):
		return 6
	
	@property
	def sensorVIncrement(self):
		return 2
	
	@property
	def sensorVMax(self):
		return 1280
	
	@property
	def sensorVMin(self):
		return 8

	@property
	def sensorHIncrement(self):
		return 16

	@property
	def sensorHMax(self):
		return 720

	@property
	def sensorHMin(self):
		return 96
	
	@property
	def sensorVDark(self):
		return 4 #VDarkRows, for calibration
	
	@property
	def sensorIso(self):
		return 320
	
	@property
	def sensorPixelRate(self):
		return 1.40198e+09
	
	@property
	def sensorTemperature(self):
		return 22.125
	
	
	
	
	
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
	def exposureNormalized(self):
		"""float: The current exposure time rescaled between `exposureMin` and `exposureMax`.  This value is 0 when exposure is at minimum, and increases linearly until exposure is at maximum, when it is 1.0."""
		return 0.5
	@exposureNormalized.setter
	def exposureNormalized(self, value):
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
	
	
	__exposureMode = 'normal'
	@property
	def exposureMode(self):
		"""str: Mode in which frame timing and exposure should operate.
		
		Args:
			'normal': Frame and exposure timing operate on fixed periods and are free-running.
			'frameTrigger': Frame starts on the rising edge of the trigger signal, and **exposes
				the frame for `exposurePeriod` nanoseconds**. Once readout completes, the camera will
				wait for another rising edge before starting the next frame. In this mode, the
				`framePeriod` property constrains the minimum time between frames.
			'shutterGating': Frame starts on the rising edge of the trigger signal, and **exposes
				the frame for as long as the trigger signal is held high**, regardless of the `exposurePeriod`
				property. Once readout completes, the camera will wait for another
				rising edge before starting the next frame. In this mode, the `framePeriod` property
				constrains the minimum time between frames. 
		"""
		return self.__exposureMode
	@exposureMode.setter
	def exposureMode(self, value):
		if not self._state == 'idle':
			raise Exception('State is not idle.')
		if value not in ('normal', 'frameTrigger', 'shutterGating'):
			raise ValueError("exposureMode value of '%s' is not supported" % (value))
		
		self.__exposureMode = value
	
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
	def currentIso(self):
		return self._gain * 5
	
	#===============================================================================================
	# API Parameters: Camera Status Group
	
	_state = 'idle' #There's going to be some interaction about what's valid when, wrt this variable and API calls.
	
	@property
	def state(self):
		return self._state
	
	@property
	def dateTime(self):
		"""str: The current date and time in ISO-8601 format."""
		return datetime.datetime.now().isoformat()
	
	@property
	def externalPower(self):
		"""bool: True when the AC adaptor is present, and False when on battery power."""
		return True
	
	@property
	def batteryChargePercent(self):
		"""float: Estimated battery charge, with 0.0 being fully depleted and 1.0 being fully charged."""
		return self.batteryChargeNormalized * 100
	
	@property
	def batteryChargeNormalized(self):
		"""float: Estimated battery charge, with 0% being fully depleted and 100% being fully charged."""
		return [1.0, 0.99, 0.98][random.randrange(3) % 3]
	
	@property
	def batteryVoltage(self):
		"""float: A measure of the power the removable battery is putting out, in volts. A happy battery outputs between 12v and 12.5v. This value is graphed on the battery screen on the Chronos."""
		return [12.45, 12.50, 12.55][random.randrange(3) % 3]
	
	@property
	def batteryPresent(self):
		"""float: A measure of the power the removable battery is putting out, in volts. A happy battery outputs between 12v and 12.5v. This value is graphed on the battery screen on the Chronos."""
		return True
	
	@property
	def batteryCritical(self):
		"""float: A measure of the power the removable battery is putting out, in volts. A happy battery outputs between 12v and 12.5v. This value is graphed on the battery screen on the Chronos."""
		return False
	
	_fanOverride = True
	@property
	def fanOverride(self):
		"""float Turn off the camera if the battery charge level, reported by `batteryChargePercent`, falls below this level. The camera will start saving any recorded footage before it powers down. If this level is too low, the camera may run out of battery and stop before it finishes saving."""
		return self._fanOverride
		
	@fanOverride.setter
	def fanOverride(self, val):
		self._fanOverride = val
		self.__propChange("saveAndPowerDownLowBatteryLevelNormalized")
		self.__propChange("fanOverride")
	
	
	_powerOffWhenMainsLost = False
	@property
	def powerOffWhenMainsLost(self):
		"""bool: Should the camera try to turn off gracefully when the battery is low? The low level is set by `saveAndPowerDownLowBatteryLevelPercent` (or `saveAndPowerDownLowBatteryLevelNormalized`). The opposite of `powerOnWhenMainsConnected`. See `powerOnWhenMainsConnected` for an example which sets the camera to turn on and off when external power is supplied."""
		return self._powerOffWhenMainsLost
		
	@powerOffWhenMainsLost.setter
	def powerOffWhenMainsLost(self, val):
		self._powerOffWhenMainsLost = val
		self.__propChange("powerOffWhenMainsLost")
	
	_powerOnWhenMainsConnected = False
	@property
	def powerOnWhenMainsConnected(self):
		"""bool: Set to `True` to have the camera turn itself on when it is plugged in. The inverse of this, turning off when the charger is disconnected, is achieved by setting the camera to turn off at any battery percentage. For example, to make the camera turn off when it is unpowered and turn on when it is powered again - effectively only using the battery to finish saving - you could make the following call: `api.set({ 'powerOnWhenMainsConnected':True, 'saveAndPowerDownWhenLowBattery':True, 'saveAndPowerDownLowBatteryLevelPercent':100.0 })`."""
		return self._powerOnWhenMainsConnected
		
	@powerOnWhenMainsConnected.setter
	def powerOnWhenMainsConnected(self, val):
		self._powerOnWhenMainsConnected = val
		self.__propChange("powerOnWhenMainsConnected")
	
	_backlightEnabled = True
	@property
	def backlightEnabled(self):
		"""bool: True if the LCD on the back of the camera is lit. Can be set to False to dim the screen and save a small amount of power."""
		return self._backlightEnabled
	@backlightEnabled.setter
	def backlightEnabled(self, value):
		pass

	@property
	def externalStorage(self):
		"""dict: The currently attached external storage partitions and their status. The sizes
		of the reported storage devices are in units of kB.
		
		Examples:
			>>> print(json.dumps(camera.externalStorage, indent=3))
			{
				\"mmcblk1p1\": {
					\"available\": 27831008,
					\"mount\": \"/media/mmcblk1p1\",
					\"used\": 3323680,
					\"device\": \"/dev/mmcblk1p1\",
					\"size\": 31154688
				}
			}
		"""
		return {
			"mmcblk1p1": {
				"available": 27831008,
				"mount": "/media/mmcblk1p1",
				"used": 3323680,
				"device": "/dev/mmcblk1p1",
				"size": 31154688
			}
		}
	
	#===============================================================================================
	# API Parameters: Camera Network Group
	_networkHostname = "chronos"
	@property
	def networkHostname(self):
		"""str: hostname to be used for dhcp requests and to be displayed on the command line.
		"""
		return self._networkHostname
	@networkHostname.setter
	def networkHostname(self, name):
		self._networkHostname = name
	
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
		return self._resolution
	
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

	#===============================================================================================
	# API Parameters: Color Space Group
	
	_wbColor = [1,1,1]
	
	@property
	def wbColor(self):
		"""Array of Red, Green, and Blue gain coefficients to achieve white balance."""
		return self._wbColor
		
	@wbColor.setter
	def wbColor(self, value):
		self._wbColor = value
	
	_wbCustomColor = [1,1,1]
	
	@property
	def wbCustomColor(self):
		"""Array of Red, Green, and Blue gain coefficients to achieve white balance."""
		return self._wbCustomColor
		
	@wbCustomColor.setter
	def wbCustomColor(self, value):
		self._wbCustomColor = value
	
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
	
	_wbTemperature = 5400 #°K
	
	@property
	def wbTemperature(self):
		"""Array of Red, Green, and Blue gain coefficients to achieve white balance."""
		return self._wbTemperature
		
	@wbTemperature.setter
	def wbTemperature(self, value):
		self._wbTemperature = value
	
	_recMaxFrames = 0
	@property
	def recMaxFrames(self):
		return self._recMaxFrames
	@recMaxFrames.setter
	def recMaxFrames(self, value):
		self._recMaxFrames = value
	
	_recMode = 'normal'
	@property
	def recMode(self):
		return self._recMode
	@recMode.setter
	def recMode(self, value):
		assert value in ('normal', 'segmented', 'burst')
		self._recMode = value
	
	_recPreBurst = 0
	@property
	def recPreBurst(self):
		return self._recPreBurst
	@recPreBurst.setter
	def recPreBurst(self, value):
		self._recPreBurst = value
	
	_recSegments = 1
	@property
	def recSegments(self):
		return self._recSegments
	@recSegments.setter
	def recSegments(self, value):
		assert value >= 1
		self._recSegments = value
	
	_recTrigDelay = 0
	@property
	def recTrigDelay(self):
		return self._recTrigDelay
	@recTrigDelay.setter
	def recTrigDelay(self, value):
		self._recTrigDelay = value

	#===============================================================================================
	# API Parameters: IO Configuration Group
	_ioMappingStopRec = {
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingStopRec(self):
		return self._ioMappingStopRec
	@ioMappingStopRec.setter
	def ioMappingStopRec(self, value):
		self._ioMappingStopRec = value
	
	_ioDetailedStatus = {
		"detailedComb": {
			"or1": 0,
			"or2": 0,
			"or3": 0,
			"xor": 1,
			"and": 1
		},
		"edgeTimers": {
			"toggle": {
				"rising": 42.9497,
				"falling": 42.9497
			},
			"stop": {
				"rising": 42.9497,
				"falling": 42.9497
			},
			"interrupt": {
				"rising": 42.9497,
				"falling": 42.9497
			},
			"io1": {
				"rising": 42.9497,
				"falling": 42.9497
			},
			"shutter": {
				"rising": 42.9497,
				"falling": 42.9497
			},
			"io2": {
				"rising": 42.9497,
				"falling": 42.9497
			},
			"start": {
				"rising": 42.9497,
				"falling": 42.9497
			}
		},
		"sources": {
			"io1": 0,
			"delay": 0,
			"nextSeg": 0,
			"io3": 0,
			"dispFrame": 0,
			"alwaysHigh": 1,
			"comb": 1,
			"none": 0,
			"toggle": 0,
			"shutter": 1,
			"endRec": 0,
			"timingIo": 1,
			"recording": 0,
			"software": 0,
			"startRec": 0,
			"io2": 0
		},
		"outputs": {
			"delay": 0,
			"start": 0,
			"comb": 1,
			"shutter": 0,
			"toggle": 0,
			"stop": 0,
			"io1": 0,
			"io2": 0
		}
	}
	@property
	def ioDetailedStatus(self):
		return self._ioDetailedStatus
	@ioDetailedStatus.setter
	def ioDetailedStatus(self, value):
		self._ioDetailedStatus = value
	
	_ioMappingCombAnd = {
		"source": "alwaysHigh",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingCombAnd(self):
		return self._ioMappingCombAnd
	@ioMappingCombAnd.setter
	def ioMappingCombAnd(self, value):
		self._ioMappingCombAnd = value
	
	_ioMappingStartRec = {
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingStartRec(self):
		return self._ioMappingStartRec
	@ioMappingStartRec.setter
	def ioMappingStartRec(self, value):
		self._ioMappingStartRec = value
	
	_ioSourceStatus = {
		"io1": 0,
		"delay": 0,
		"nextSeg": 0,
		"io3": 0,
		"dispFrame": 0,
		"alwaysHigh": 1,
		"comb": 1,
		"none": 0,
		"toggle": 0,
		"shutter": 1,
		"endRec": 0,
		"timingIo": 1,
		"recording": 0,
		"software": 0,
		"startRec": 0,
		"io2": 0
	}
	@property
	def ioSourceStatus(self):
		return self._ioSourceStatus
	@ioSourceStatus.setter
	def ioSourceStatus(self, value):
		self._ioSourceStatus = value
	
	_ioMappingToggleClear = {
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingToggleClear(self):
		return self._ioMappingToggleClear
	@ioMappingToggleClear.setter
	def ioMappingToggleClear(self, value):
		self._ioMappingToggleClear = value
	
	_ioThresholdIo2 = 2.50271
	@property
	def ioThresholdIo2(self):
		return self._ioThresholdIo2
	@ioThresholdIo2.setter
	def ioThresholdIo2(self, value):
		self._ioThresholdIo2 = value
	
	_ioThresholdIo1 = 2.50271
	@property
	def ioThresholdIo1(self):
		return self._ioThresholdIo1
	@ioThresholdIo1.setter
	def ioThresholdIo1(self, value):
		self._ioThresholdIo1 = value
	
	_ioDelayTime = 0
	@property
	def ioDelayTime(self):
		return self._ioDelayTime
	@ioDelayTime.setter
	def ioDelayTime(self, value):
		self._ioDelayTime = value
	
	_ioMappingCombOr1 = {
		"source": "none",
		"debounce": 1,
		"invert": 0
	}
	@property
	def ioMappingCombOr1(self):
		return self._ioMappingCombOr1
	@ioMappingCombOr1.setter
	def ioMappingCombOr1(self, value):
		self._ioMappingCombOr1 = value
	
	_ioMappingCombOr2 = {
		"source": "none",
		"debounce": 1,
		"invert": 0
	}
	@property
	def ioMappingCombOr2(self):
		return self._ioMappingCombOr2
	@ioMappingCombOr2.setter
	def ioMappingCombOr2(self, value):
		self._ioMappingCombOr2 = value
	
	_ioMappingIo2 = {
		"drive": 0,
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingIo2(self):
		return self._ioMappingIo2
	@ioMappingIo2.setter
	def ioMappingIo2(self, value):
		self._ioMappingIo2 = value
	
	_ioOutputStatus = {
		"delay": 0,
		"start": 0,
		"comb": 1,
		"shutter": 0,
		"toggle": 0,
		"stop": 0,
		"io1": 0,
		"io2": 0
	}
	@property
	def ioOutputStatus(self):
		return self._ioOutputStatus
	@ioOutputStatus.setter
	def ioOutputStatus(self, value):
		self._ioOutputStatus = value
	
	_ioMappingTrigger = {
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingTrigger(self):
		return self._ioMappingTrigger
	@ioMappingTrigger.setter
	def ioMappingTrigger(self, value):
		self._ioMappingTrigger = value
	
	_ioMappingCombXor = {
		"source": "alwaysHigh",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingCombXor(self):
		return self._ioMappingCombXor
	@ioMappingCombXor.setter
	def ioMappingCombXor(self, value):
		self._ioMappingCombXor = value
	
	_ioMappingShutter = {
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingShutter(self):
		return self._ioMappingShutter
	@ioMappingShutter.setter
	def ioMappingShutter(self, value):
		self._ioMappingShutter = value
	
	_ioMappingToggleFlip = {
		"source": "comb",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingToggleFlip(self):
		return self._ioMappingToggleFlip
	@ioMappingToggleFlip.setter
	def ioMappingToggleFlip(self, value):
		self._ioMappingToggleFlip = value
	
	_ioMappingCombOr3 = {
		"source": "none",
		"debounce": 1,
		"invert": 0
	}
	@property
	def ioMappingCombOr3(self):
		return self._ioMappingCombOr3
	@ioMappingCombOr3.setter
	def ioMappingCombOr3(self, value):
		self._ioMappingCombOr3 = value
	
	_ioMappingToggleSet = {
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingToggleSet(self):
		return self._ioMappingToggleSet
	@ioMappingToggleSet.setter
	def ioMappingToggleSet(self, value):
		self._ioMappingToggleSet = value
	
	_ioMappingDelay = {
		"source": "toggle",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingDelay(self):
		return self._ioMappingDelay
	@ioMappingDelay.setter
	def ioMappingDelay(self, value):
		self._ioMappingDelay = value
	
	_ioMappingIo1 = {
		"drive": 0,
		"source": "none",
		"debounce": 0,
		"invert": 0
	}
	@property
	def ioMappingIo1(self):
		return self._ioMappingIo1
	@ioMappingIo1.setter
	def ioMappingIo1(self, value):
		self._ioMappingIo1 = value
	
	
	#===============================================================================================
	# API Parameters: Misc
	
	__miscScratchPad = {}
	@property
	def miscScratchPad(self):
		if self.__miscScratchPad == {}:
			return {"empty":True}
		else:
			return self.__miscScratchPad
	@miscScratchPad.setter
	def miscScratchPad(self, value):
		for key,value in value.items():
			if value is None or value == 'null':
				if key in self.__miscScratchPad:
					del self.__miscScratchPad[key]
			else:
				self.__miscScratchPad[key] = value

		self.__propChange('miscScratchPad')
	

	#===============================================================================================
	# Camera parameters.
	@property
	def totalFrames(self):
		return 10000
	
	@totalFrames.setter
	def totalFrames(self, value):
		pass
	
	_totalSegments = 0
	@property
	def totalSegments(self):
		return self._totalSegments
	@totalSegments.setter
	def totalSegments(self, value):
		self._totalSegments = value
	
	_focusPeakingColor = 'Red'
	@property
	def focusPeakingColor(self):
		return self._focusPeakingColor
	@focusPeakingColor.setter
	def focusPeakingColor(self, value):
		self._focusPeakingColor = value
	
	_focusPeakingLevel = 0
	@property
	def focusPeakingLevel(self):
		return self._focusPeakingLevel
	@focusPeakingLevel.setter
	def focusPeakingLevel(self, value):
		self._focusPeakingLevel = value
	
	_zebraLevel = 0
	@property
	def zebraLevel(self):
		return self._zebraLevel
	@zebraLevel.setter
	def zebraLevel(self, value):
		self._zebraLevel = value
	
	_overlayEnable = 0
	@property
	def overlayEnable(self):
		return self._overlayEnable
	@overlayEnable.setter
	def overlayEnable(self, value):
		self._overlayEnable = value
	
	_overlayFormat = "frame %d"
	@property
	def overlayFormat(self):
		return self._overlayFormat
	@overlayFormat.setter
	def overlayFormat(self, value):
		self._overlayFormat = value
	
	_playbackLength = 10000
	@property
	def playbackLength(self):
		return self._playbackLength
	@playbackLength.setter
	def playbackLength(self, value):
		self._playbackLength = value
	
	_playbackPosition = 0
	@property
	def playbackPosition(self):
		return self._playbackPosition
	@playbackPosition.setter
	def playbackPosition(self, value):
		self._playbackPosition = value
	
	_playbackRate = 60
	@property
	def playbackRate(self):
		return self._playbackRate
	@playbackRate.setter
	def playbackRate(self, value):
		self._playbackRate = value
	
	_playbackStart = 0
	@property
	def playbackStart(self):
		return self._playbackStart
	@playbackStart.setter
	def playbackStart(self, value):
		self._playbackStart = value
	
	_playbackStart = 0
	@property
	def playbackStart(self):
		return self._playbackStart
	@playbackStart.setter
	def playbackStart(self, value):
		self._playbackStart = value
	
	_shippingMode = False
	@property
	def shippingMode(self):
		return self._shippingMode
	@shippingMode.setter
	def shippingMode(self, value):
		self._shippingMode = value
	
	@property
	def videoState(self):
		return 'live'
	




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
		state._state = state
		self.emitControlSignal('state')
		
		def done():
			state._state = 'idle'
			self.emitControlSignal('state')
			
		timer = QTimer(self)
		timer.timeout.connect(done)
		timer.setSingleShot(True)
		timer.start(duration) #ms
	
	
	@action('get')
	@pyqtSlot('QVariantList', result='QVariantMap')
	def get(self, keys: List[str]): #Dict[str, Any]
		retval = {}
		
		for key in keys:
			if key[0] == '_' or not hasattr(state, key): # Don't allow querying of private variables.
				#QDBusMessage.createErrorReply does not exist in PyQt5, and QDBusMessage.errorReply can't be sent. As far as I can tell, we simply can not emit D-Bus errors.
				#Can't reply with a single string, either, since QVariantMap MUST be key:value pairs and we don't seem to have unions or anything.
				#The type overloading, as detailed at http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator, simply does not work in this case. The last pyqtSlot will override the first pyqtSlot with its return type.
				return MockError('ValueError', f"The value '{key}' is not a known key to get.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
			
			retval[key] = getattr(state, key)
		
		return retval
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def set(self, data: dict):
		# Check all errors first to avoid partially applying an update.
		for key, value in data.items():
			if key[0] == '_' or not hasattr(state, key):  # Don't allow setting of private variables.
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
	def status(self, *_):
		return {'state': state._state}
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def doReset(self, *_) -> None:
		print('resetting...')
		self.holdState('reinitializing', 500)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startAutoWhiteBalance(self, *_) -> None:
		print('auto white balancing...')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def revertAutoWhiteBalance(self, *_) -> None:
		print('reset white balance')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startBlackCalibration(self, *_) -> None:
		print('starting black calibration...')
		self.holdState('calibrating', 2000)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startZeroTimeBlackCal(self, *_) -> None:
		print('starting zero-time black calibration...')
		self.holdState('calibrating', 2000)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startAnalogCalibration(self, *_) -> None:
		print('starting analog calibration...')
		self.holdState('calibrating', 2000)
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def startRecording(self, *_) -> None:
		state._state = 'recording'
		self.emitControlSignal('state')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def stopRecording(self, *_) -> None:
		state._state = 'idle'
		self.emitControlSignal('state')
		return self.status()
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def getResolutionTimingLimits(self, *_) -> None:
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