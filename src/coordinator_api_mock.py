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


class Reply(Dict):
	"""D-Bus Reply class. Encapsulates standard error and value.
		
		Construct with a value and return from a D-Bus call (a
		pyqtSlot(…, return='QVariantMap')-decorated function).
		
		Alternately, construct with an errorName (str) and message
		(str) and return to indicate an error. (If errorName is not
		supplied, message should be ignored.)"""
	
	def __init__(self, *args):
		if not args:
			pass #easy: no return value, no error, do nothing
		elif len(args) == 1:
			self['value'] = args[0]
		elif len(args) == 2:
			self['errorName'] = args[0]
			self['message'] = args[1]
		else:
			raise ValueError(f'Reply expected 1 or 2 args, got {len(args)}.')


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
#    Pure Functions    #
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
#    Callbacks for Set Values    #
##################################


#Pending callbacks is used by state callbacks to queue long-running or multi
#arg tasks such as changeRecordingResolution. This is so a call to set which
#contains x/y/w/h of a new camera resolution only actually resets the camera
#video pipeline once. Each function which appears in the list is called only
#once, after all values have been set.
pendingCallbacks = set()


def changeRecordingResolution(state):
	if state.videoState == 'preview':
		print(f"Mock: changing recording resolution to xywh {state.previewHOffset} {state.previewVOffset} {state.previewHRes} {state.previewVRes}.")
	else:
		print(f"Mock: changing recording resolution to xywh {state.recordingHOffset} {state.recordingVOffset} {state.recordingHRes} {state.recordingVRes}.")


def notifyExposureChange(state):
	print('Mock: Exposure change callback.')
	#self.emitControlSignal('maxExposureNs', 7e8) # Example.
	#self.emitControlSignal('minExposureNs', 3e2)



#######################################
#    Mock D-Bus Interface Provider    #
#######################################

class State():
	#Invariant data about the camera.
	cameraModel = "Mock Camera 1.4"
	cameraApiVersion = '0.1.0' #This should probably be git tag, if available, or revision if not.
	cameraFpgaVersion = '3.15'
	cameraMemoryGB = 16.
	cameraSerial = "Captain Crunch"
	cameraDescription = "Chronos SN:Captain Crunch"
	sensorName = "acme9001"
	sensorHMax = 1280
	sensorHMin = 256
	sensorVMax = 1024
	sensorVMin = 64
	sensorHIncrement = 2
	sensorVIncrement = 32
	sensorPixelRate = 1920 * 1080 * 1000
	sensorPixelFormat = "BYR2" #Or "y12" for mono models.
	sensorRecordsColor = True
	
	sensorQuantizeTimingNs = 250
	sensorMinExposureNs = int(1e1)
	sensorMaxExposureNs = int(1e9)
	sensorMaxShutterAngle = 330
	timingMaxPeriod = sys.maxsize
	
	@property
	def timingMinPeriod(self):
		return (state.recordingHRes * state.recordingVRes * int(1e9)) / state.sensorPixelRate
	
	timingMinExposureNs = sensorMinExposureNs
	timingMaxExposureNs = sensorMaxExposureNs
	timingExposureDelayNs = 960
	timingQuantization = 1e9 / sensorQuantizeTimingNs
	
	
	@property
	def timingMaxShutterAngle(self):
		return self.timingMaxExposureNs/self.timingExposureDelayNs * 359
	
	@timingMaxShutterAngle.setter
	def timingMaxShutterAngle(self, value):
		self._recordingHOffset = value
		self.timingExposureDelayNs = value/359 * self.timingMaxExposureNs
		self.emitControlSignal('timingExposureDelayNs')
	
	
	
	@property
	def commonlySupportedResolutions(self): 
		return [{
			'hRes': x, 
			'vRes': y, 
			'framerate': framerateForResolution(x, y),
		} for x, y in [
			[1280, 1024],
			[1280, 720],
			[1280, 512],
			[1280, 360],
			[1280, 240],
			[1280, 120],
			[1280, 96],
			[1024, 768],
			[1024, 576],
			[800, 600],
			[800, 480],
			[640, 480],
			[640, 360],
			[640, 240],
			[640, 120],
			[640, 96],
			[336, 240],
			[336, 120],
			[336, 96],
		]]
	
	@property
	def externallyPowered(self):
		return random.choice((True, False))
	
	@property
	def batteryCharge(self):
		return random.choice((1., .99, .98, .97, .96))

	@property
	def batteryVoltage(self):
		return random.choice((12.38, 12.38, 12.39, 12.39, 12.40))
	
	
	_recordingHRes = 200 #rebuilds video pipeline
	
	@property
	def recordingHRes(self): #rebuilds video pipeline
		return self._recordingHRes
	
	@recordingHRes.setter
	def recordingHRes(self, value):
		global pendingCallbacks
		self._recordingHRes = value
		pendingCallbacks |= set([changeRecordingResolution, notifyExposureChange])
		
	@property
	def recordingHStep(self): #constant, we only have the one sensor
		return 16
	
	
	_recordingVRes = 300 
	
	@property
	def recordingVRes(self): 
		return self._recordingVRes
	
	@recordingVRes.setter
	def recordingVRes(self, value):
		global pendingCallbacks
		self._recordingVRes = value
		pendingCallbacks |= set([changeRecordingResolution, notifyExposureChange])
	
	@property
	def recordingVStep(self): #constant, we only have the one sensor
		return 2
	
	
	_recordingHOffset = 800 #rebuilds video pipeline
	
	@property
	def recordingHOffset(self): #rebuilds video pipeline
		return self._recordingHOffset
	
	@recordingHOffset.setter
	def recordingHOffset(self, value):
		global pendingCallbacks
		self._recordingHOffset = value
		pendingCallbacks |= set([changeRecordingResolution])
	
	
	_recordingVOffset = 480
	
	@property
	def recordingVOffset(self):
		return self._recordingVOffset
	
	@recordingVOffset.setter
	def recordingVOffset(self, value):
		global pendingCallbacks
		self._recordingVOffset = value
		pendingCallbacks |= set([changeRecordingResolution])
	
	
	recordingAnalogGainMultiplier = 2 #doesn't rebuild video pipeline, only takes gain multiplier
	
	
	_previewHRes = 200 #rebuilds video pipeline
	
	@property
	def previewHRes(self): #rebuilds video pipeline
		return self._previewHRes
	
	@previewHRes.setter
	def previewHRes(self, value):
		global pendingCallbacks
		self._previewHRes = value
		pendingCallbacks |= set([changeRecordingResolution, notifyExposureChange])
	
	
	_previewVRes = 300 
	
	@property
	def previewVRes(self): 
		return self._previewVRes
	
	@previewVRes.setter
	def previewVRes(self, value):
		global pendingCallbacks
		self._previewVRes = value
		pendingCallbacks |= set([changeRecordingResolution, notifyExposureChange])
	
	
	_previewHOffset = 800 #rebuilds video pipeline
	
	@property
	def previewHOffset(self): #rebuilds video pipeline
		return self._previewHOffset
	
	@previewHOffset.setter
	def previewHOffset(self, value):
		global pendingCallbacks
		self._previewHOffset = value
		pendingCallbacks |= set([changeRecordingResolution])
	
	
	_previewVOffset = 480
	
	@property
	def previewVOffset(self):
		return self._previewVOffset
	
	@previewVOffset.setter
	def previewVOffset(self, value):
		global pendingCallbacks
		self._previewVOffset = value
		pendingCallbacks |= set([changeRecordingResolution])
	
	
	previewAnalogGainMultiplier = 2 #doesn't rebuild video pipeline, only takes gain multiplier
	
	
	@property
	def availableRecordingAnalogGains(self) -> list: 
		return [{"multiplier":2**i, "dB":6*i} for i in range(0,5)]
	
	
	_sensorMilliframerate = int(1500e3)
	
	@property
	def sensorMilliframerate(self):
		return self._sensorMilliframerate
	
	@sensorMilliframerate.setter
	def sensorMilliframerate(self, value):
		newMaxRecordingPeriod = int(1e9/(value/1000))
		if newMaxRecordingPeriod < self.recordingPeriod:
			print('notification: new max recording period less than recording period')
			#Perhaps we want to bump the recording period down? I think it would make
			#sense for these numbers to generally "trail" each other. Or should it be
			#a proportional thing? Like exposure is always n% of the frame? I think
			#that might make more sense… so it's a shutter angle we actually store?
		self._sensorMilliframerate = value
	
	
	recordingExposureNs = int(850) #These don't have to have the pipeline torn down, so they don't need the hack where we set video settings atomically.
		
	@property
	def recordingPeriod(self):
		return self.recordingExposureNs + 5000
	
	@recordingPeriod.setter
	def recordingPeriod(self, value):
		global pendingCallbacks
		if value > 5000: 
			raise ValueError("Recording period is 5000ns greater than recording exposure - since exposure can't be negative, the total recording period can't be less than 5000.")
		self.recordingExposureNs = value - 5000
	
	#rectangle of the video display area
	videoDisplayDevice = "camera" #or "http". "camera" includes hdmi out. Not sure if this value is needed, depends if we can get video out over http at the same time we can display it on the back of the camera.
	videoDisplayX = 0
	videoDisplayY = 0
	videoDisplayWidth = 200
	videoDisplayHeight = 200
	
	_videoState = 'pre-recording' #There's going to be some interaction about what's valid when, wrt this variable and API calls.
	
	@property
	def videoState(self):
		return self._videoState
	
	@videoState.setter
	def videoState(self, value):
		global pendingCallbacks
		assert value in {'pre-recording', 'recording', 'playback', 'saving', 'preview'}
		if 'preview' in (self._videoState, value):
			pendingCallbacks |= set([changeRecordingResolution])
		self._videoState = value
	
	totalAvailableFrames = 80000 #This is the number of frames we *can* record. There is some overhead for each frame, so the increase in frames as we decrease resolution is not quite linear.
	
	playbackFrame = 0
	playbackFramerate = 0 #Set this to play or rewind the video.
	totalRecordedFrames = 80000 #This only changes when we have a full segment recorded. Proposal: It does not change while recording. It changes at maximum rate of 30hz, in case segments are extremely short, in which case it may skip intermediate segments.
	
	triggerDelay = 0 #signed int, between -lots and totalAvailableFrames
	
	focusPeakingColor = 0xff0000 #red, green, blue (RGB), like CSS colors.
	focusPeakingIntensity = 'low' #One of ['off', 'low', 'medium', 'high'].
	showWhiteClippingZebraStripes = True
	showBlackClippingZebraStripes = True
	disableOverwritingRingBuffer = False #In segmented mode, disable overwriting earlier recorded ring buffer segments. DDR 2018-06-19: Loial figures this was fixed, but neither of us know why it's hidden in the old UI.
	
	recordingMode = 'normal' #Normal, segmented, or gated burst.
	recordingSegments = int(1e9)
	recordedSegments = [{ #Each entry in this list a segment of recorded video. Although currently resolution/framerate is always the same having it in this data will make it easier to fix this in the future if we do.
		"start": 0,
		"end": 5000,
		"hres": 200,
		"vres": 300,
		"milliframerate": 12580e3,
		"id": "ldPxTT5R",
	},{
		"start": 5000,
		"end": 80000,
		"hres": 200,
		"vres": 500,
		"milliframerate": 900e3,
		"id": "KxIjG09V",
	}]
	whiteBalance = [1., 1., 1.]
	colorMatrix = [
		[1,0,0],
		[0,1,0],
		[0,0,1],
	]
	triggerDelayNs = int(1e9)
	
	triggerConfiguration = { #read/write, what the triggers do
		"trig1": {
			"action": random.choice(['none', 'record end', 'exposure gating', 'genlock in', 'genlock out']),
			"threshold": 2.50,
			"invert": False,
			"debounce": True,
			"pullup1ma": False,
			"pullup20ma": True,
		},
		"trig2": {
			"action": random.choice(['none', 'record end', 'exposure gating', 'genlock in', 'genlock out']),
			"threshold": 2.75,
			"invert": True,
			"debounce": True,
			"pullup1ma": False,
			"pullup20ma": False,
		},
		"trig3": {
			"action": random.choice(['none', 'record end']),
			"threshold": 2.50,
			"invert": False,
			"debounce": False,
			"pullup1ma": True,
			"pullup20ma": True,
		},
		"~a1": {
			"action": "none",
			"threshold": 2.50,
			"invert": False,
			"debounce": True,
			"pullup1ma": False,
			"pullup20ma": True,
		},
		"~a2": {
			"action": "none",
			"threshold": 2.50,
			"invert": False,
			"debounce": True,
			"pullup1ma": False,
			"pullup20ma": True,
		},
		"motion": {
			"action": random.choice(['none', 'record end']),
			"threshold": 2.50,
			"invert": False,
			"debounce": True,
			"pullup1ma": False,
			"pullup20ma": True,
		},
	}
	
	@property
	def triggerCapabilities(self): #read, what the triggers are capable of
		return {
			"trig1": {                     # id
				"name": "Trigger 1 (BNC)", # full name (human-readable label)
				"label": "TRIG1",          # short name (as printed on the case)
				"thresholdMin": 0.,
				"thresholdMax": 7.2,
				"pullup1ma": True,
				"pullup20ma": True,
				"outputCapable": True,
				"motion": False,
			},
			"trig2": {
				"name": "Trigger 2",
				"label": "TRIG2",
				"thresholdMin": 0.,
				"thresholdMax": 7.2,
				"pullup1ma": False,
				"pullup20ma": True,
				"outputCapable": True,
				"motion": False,
			},
			"trig3": {
				"name": "Trigger 3 (isolated)",
				"label": "TRIG3",
				"thresholdMin": 0.,
				"thresholdMax": 7.2,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
				"motion": False,
			},
			"~a1": { #DDR 2018-06-18: I don't know what the analog input settings will be like.
				"name": "Analog 1",
				"label": "~A1",
				"thresholdMin": 0.,
				"thresholdMax": 7.2,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
				"motion": False,
			},
			"~a2": {
				"name": "Analog 2",
				"label": "~A2",
				"thresholdMin": 0.,
				"thresholdMax": 7.2,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
				"motion": False,
			},
			"motion": {
				"name": "Motion",
				"label": "",
				"thresholdMin": False,
				"thresholdMax": False,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
				"motion": True,
			},
		}
	
	@property
	def triggers(self):
		return list(self.triggerCapabilities.keys())
	
	@property
	def triggerState(self):
		return {
			"trig1": {
				"inputIsActive": random.choice((True, False)), #such modelling, so sophisticated 🖏 
				"level": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"trig2": {
				"inputIsActive": random.choice((True, False)),
				"level": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"trig3": {
				"inputIsActive": random.choice((True, False)),
				"level": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"~a1": {
				"inputIsActive": random.choice((True, False)),
				"level": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"~a2": {
				"inputIsActive": random.choice((True, False)),
				"level": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"motion": {
				"inputIsActive": random.choice((True, False)),
				"level": random.choice((0., 0, 0.01, 0.01, 0.01, 0.01, 0.07))
			},
		}
	
	motionTriggerHOffset = 134
	motionTriggerVOffset = 656
	motionTriggerHRes = 64
	motionTriggerVRes = 800
	motionTriggerAdaption = "low" #one of high, medium, low, off
	
	#Overlay has moved to Video API
	#
	#overlayVersion = "1.1"
	#
	#overlayTextbox0Content = 'textbox 0 sample text'
	#overlayTextbox0Font = list(b'<binary font data here>')
	#overlayTextbox0Color = 0xFFFFFF20 #RGBA
	#overlayTextbox0X = 0x0008
	#overlayTextbox0Y = 0x0010
	#overlayTextbox0W = 0x02D0
	#overlayTextbox0H = 0x0028
	#overlayTextbox0OffsetX = 0x08
	#overlayTextbox0OffsetY = 0x08
	#
	#overlayTextbox1Content = 'textbox 1 sample text'
	#overlayTextbox1Font = list(b'<binary data here>')
	#overlayTextbox1Color = 0xFFFFFF20 #RGBA
	#overlayTextbox1X = 0x0110
	#overlayTextbox1Y = 0x03D8
	#overlayTextbox1W = 0x0320
	#overlayTextbox1H = 0x0028
	#overlayTextbox1OffsetX = 0x08
	#overlayTextbox1OffsetY = 0x08
	#
	#overlayChronosWatermarkColor = 0x20202020 #RGBA
	#overlayChronosWatermarkX = 0x0008
	#overlayChronosWatermarkY = 0x02F8
	#
	#overlayRGBImage = list(b'<binary data here>')
	#overlayRGBLogoPalette = list(b'<binary LUT here>')
	#overlayRGBImageX = 0x0190
	#overlayRGBImageY = 0x0258
	#overlayRGBImageWidth = 0x0080
	#overlayRGBImageHeight = 0x0080
	
	dimScreenWhenNotInUse = False
	saveAndPowerDownWhenLowBattery = False
	saveAndPowerDownLowBatteryLevel = 0.77
	powerOnWhenMainsConnected = True
	
	datetime = "2018-09-20T13:23:23.036586" #iso 8601, YYYY-MM-DDTHH:MM:SS.mmmmmm as detailed at https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat
	
	@property
	def externalStorage(self) -> List[Dict[str, Union[str, int]]]:
		"""External storage device partitions.
			
			Returns a list of maps, one map per partition on each
				external storage device. (Storage devices are things
				like SD cards, USB thumb sticks, etc.)
			
			Maps contain the following keys:
				name: The given name of the partition.
				device: The name of the device the partition is on.
					If a device has more than one partition, each
					partition will have the same device name.
				path: Where in the [camera] filesystem the device is
					mounted to. Unlike name, guaranteed to be unique.
				size: The amount of space on the partition, in bytes.
				free: The amount of available space on the partition,
					in bytes. Note that size and free may not fit in
					a 32-bit integer.
				interface: Either a "usb" drive, an "sd" card port,
					or a "network" mount.
			"""
		
		return [{
			"name": "Testdisk",
			"device": "mmcblk0p1",
			"path": "/dev/sda",
			"size": 1294839100, #bytes, 64-bit positive integer
			"free": 4591,
			"interface": "usb", #"usb" or "sd"
		},{
			"name": "Toastdesk",
			"device": "sdc1",
			"path": "/dev/sdc1",
			"size": 2930232316000,
			"free": 1418341032982,
			"interface": "usb", 
		}]
	
	networkPassword = 'chronos' #Change this to be initally blank in the non-mock API. A blank password *means* no network access at all.
	localHTTPAccess = True #If this changes, something must shut down or start the web server. The only thing the server will do is start up on the right HTTP port; it will even need to be restarted if that changes. (However, the server does not need to be restarted for changes to the password. The hash is re-updated as it changes.)
	localSSHAccess = True
	remoteHTTPAccess = True
	remoteSSHAccess = True
	HTTPPort = 80
	SSHPort = 22
	
	networkStorageAddress = "smb://192.168.1.201/Something"
	networkStorageUsername = "ns username"
	_networkStoragePassword = "ns password" #This can't be a secure storage method, but I don't know how else to do it. Perhaps there is no way? Do we have a keychain on the OS we can use that would help, given we don't have password-authenticated logins?
	
	@property
	def networkStoragePassword(self):
		return "•••••••" if self._networkStoragePassword else "" #Don't make reading out the password easy, at least. This interface should support write-only passwords in the future, too.
	
	@networkStoragePassword.setter
	def networkStoragePassword(self, value):
		self._networkStoragePassword = value
	
	@property
	def networkInterfaces(self) -> List[Dict[str,str]]:
		"""Roughly; the enumeration of attached, active network devices."""
		return [{
			'id': 'enp0s25',
			'name': 'Ethernet',
			'localAddress4': '192.168.1.135',
			'localAddress6': 'fe80::22c3:8fff:fe3b:966a',
			'remoteAddress4': '205.250.126.92',
			'remoteAddress6': '',
		},{
			'id': 'wlp4s0',
			'name': 'Mini USB',
			'localAddress4': '192.168.12.1',
			'localAddress6': 'fe80::f81b:26ff:fee7:24dd',
			'remoteAddress4': '',
			'remoteAddress6': '',
		}]


state = State() #Must be instantiated for QDBusMarshaller. 🙂


class ControlAPIMock(QObject):
	"""Function calls of the camera control D-Bus API.
		
		Any function decorated by a @pyqtSlot is callable over D-Bus.
		The action decorator is used by the HTTP API, so it knows
		what caching scheme it should use."""
	
	def __init__(self):
		super().__init__()
		
		# Inject some fake update events.
		def test1():
			state.recordingExposureNs = int(8e8)
			self.emitControlSignal('recordingExposureNs')
			
		self._timer1 = QTimer()
		self._timer1.setTimerType(Qt.PreciseTimer)
		self._timer1.timeout.connect(test1)
		self._timer1.setSingleShot(True)
		self._timer1.start(1000) #ms
		
		def test2():
			state.recordingExposureNs = int(2e8)
			self.emitControlSignal('recordingExposureNs')
			
		self._timer2 = QTimer()
		self._timer2.setTimerType(Qt.PreciseTimer)
		self._timer2.timeout.connect(test2)
		self._timer2.setSingleShot(True)
		self._timer2.start(2000) #ms
		
		def test3():
			state.recordingExposureNs = int(8.5e8)
			self.emitControlSignal('recordingExposureNs')
			
		self._timer3 = QTimer()
		self._timer3.setTimerType(Qt.PreciseTimer)
		self._timer3.timeout.connect(test3)
		self._timer3.setSingleShot(True)
		self._timer3.start(3000) #ms
		
		def test4():
			state.totalRecordedFrames = 80000
			self.emitControlSignal('totalRecordedFrames')
			
		self._timer4 = QTimer()
		self._timer4.setTimerType(Qt.PreciseTimer)
		self._timer4.timeout.connect(test4)
		self._timer4.setSingleShot(True)
		self._timer4.start(1000) #ms
	
	def emitSignal(self, signalName: str, *args) -> None:
		"""Emit an arbitrary signal. (Use emitControlSignal for API values.)"""
		signal = QDBusMessage.createSignal('/com/krontech/chronos/control_mock', 'com.krontech.chronos.control_mock', signalName)
		for arg in args:
			signal << arg
		QDBusConnection.systemBus().send(signal)
	
	def emitControlSignal(self, name: str, value=None) -> None:
		"""Emit an update signal, usually for indicating a value has changed."""
		signal = QDBusMessage.createSignal('/com/krontech/chronos/control_mock', 'com.krontech.chronos.control_mock', name)
		signal << getattr(state, name) if value is None else value
		QDBusConnection.systemBus().send(signal)
	
	def emitError(self, message: str) -> None:
		error = QDBusMessage.createError('failed', message)
		QDBusConnection.systemBus().send(error)
	
	
	@action('get')
	@pyqtSlot('QVariantList', result='QVariantMap')
	def get(self, keys: List[str]) -> Reply: #Dict[str, Any]
		retval = {}
		
		for key in keys:
			if key[0] is '_' or not hasattr(state, key): # Don't allow querying of private variables.
				#QDBusMessage.createErrorReply does not exist in PyQt5, and QDBusMessage.errorReply can't be sent. As far as I can tell, we simply can not emit D-Bus errors.
				#Can't reply with a single string, either, since QVariantMap MUST be key:value pairs and we don't seem to have unions or anything.
				#The type overloading, as detailed at http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator, simply does not work in this case. The last pyqtSlot will override the first pyqtSlot with its return type.
				return Reply('ValueError', dump(f"The value '{key}' is not a known key to set.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}"))
			
			retval[key] = getattr(state, key)
		
		return Reply(retval)
	
	
	@action('set')
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def set(self, data: dict) -> Reply:
		# Check all errors first to avoid partially applying an update.
		for key, value in data.items():
			if key[0] is '_' or not hasattr(state, key):  # Don't allow setting of private variables.
				# return self.sendError('unknownValue', f"The value '{key}' is not known.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
				return Reply('ValueError', (f"The value '{key}' is not a known key to set.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}"))
			if not isinstance(value, type(getattr(state, key))):
				return Reply('ValueError', (f"Can not set '{key}', currently {getattr(state, key)}, to {value}.\nExpected {type(getattr(state, key))}, got {type(value)}."))
		
		# Set only changed variables. Changing can be quite involved, such as with recordingHRes.
		for key, value in data.items():
			if getattr(state, key) != value:
				setattr(state, key, value)
				self.emitControlSignal(key)
				print(f"MOCK: updated {key} to {value}")
				
		
		#Call each callback set. Good for multi-arg tasks such as recording resolution and trigger state.
		for cb in pendingCallbacks:
			cb(state)
		pendingCallbacks.clear()
		
		return Reply()
	
	
	@action('get')
	@pyqtSlot(result="QVariantMap")
	def availableKeys(self) -> List[str]:
		keys = [i for i in dir(state) if i[0] != '_'] #Don't expose private items.
		return Reply(keys)
	
	
	@action('get')
	@pyqtSlot(result="QVariantMap")
	def availableCalls(self) -> List[Dict[str, str]]:
		return Reply([{
			"name": i,
			"args": { #Return args: type, stripping class down to string name for D-Bus.
				argName: stringifyTypeClasses(typeClass) 
				for argName, typeClass in 
				get_type_hints(getattr(self, i)).items()
			},
			"action": getattr(self, i)._action, #Type
		} for i in self.__class__.__dict__ 
			if hasattr(getattr(self, i), '_action') ])
	
	
	@action('set')
	@pyqtSlot()
	def powerDown(self) -> None:
		print('powering down camera…')
		print('aborted, mock will not shut down machine')
		
	
	@action('get')
	@pyqtSlot(int, int, result="QVariantMap")
	def framerateForResolution(self, hRes: int, vRes: int) -> int:
		return Reply(framerateForResolution(hRes, vRes))
	
	@action('get')
	@pyqtSlot(result="QVariantMap")
	def resolutionIsValid(self, hOffset: int, vOffset: int, hRes: int, vRes: int) -> bool: #xywh px
		return Reply(resolutionIsValid(hOffset, vOffset, hRes, vRes))
	
	
	@action('set')
	@pyqtSlot("QVariantMap", result="QVariantMap")
	def calibrate(self, what) -> None:
		print(f'Mock: not calibrating {", ".join([t for t, b in what.items() if b])}.')
		return Reply()
	
	
	@action('set')
	@pyqtSlot()
	def takeStillReferenceForMotionTriggering(self) -> None:
		print('MOCK: train stillness for motion triggering')
	
	
	@action('set')
	@pyqtSlot(str, result='QVariantMap')
	def saveCameraSettings(self, toFolder: str) -> Union[Dict[str, str], None]:
		print(f'MOCK: Save calibration data to {toFolder}.')
		return (
			Reply("out of space", "Out of space on sda.") 
			if 'sda' in toFolder else 
			Reply()
		)
	
	@action('set')
	@pyqtSlot(str, result='QVariantMap')
	def loadCameraSettings(self, fromFolder: str):
		print(f'MOCK: Load calibration data.')
		return None
	
	@action('set')
	@pyqtSlot(str, result='QVariantMap')
	def resetCameraSettings(self, fromFolder: str):
		print(f'MOCK: Reset calibration data.')
		return None
	
	@action('set')
	@pyqtSlot(str)
	def applySoftwareUpdate(self, fromFolder: str):
		print(f'MOCK: Apply software update.')
		return None
	
	@action('get')
	@pyqtSlot("QVariantMap", result='QVariantMap')
	def waterfallMotionMap(self, options) -> Dict[str, Union[str, bytearray]]:
		"""Get a waterfall-style heatmap of recorded movement.
		
			Generate a heatmap from each of the 16 quadrants of
			recorded motion data. Returns an 16×n greyscale bitmap,
			one byte per pixel.
			
			Arguments are a map specifying:
				segment: What segment ID to query. If not supplied,
					all recorded data will be considered "the segment".
				startFrame = 0: Optional frame to start from. Defaults
					to the first frame of the segment.
				endFrame = ∞: Optional frame to end at. Defaults to
					the last frame of the segment.
			
			Segment IDs, and their respective startFrame and
				endFrames, can be read from the recordedSegments value."""
		
		startFrame = options.get('startFrame', 0)
		startFrame = startFrame % 1024 #Cycle period of data below.
		
		allMockFrameData = ([
			[0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0xED, 0x00, 0x88, 0xFF, 0x3F, 0xFF, 0xF5, 0xEA, 0xAF, 0x46, 0x8E],
			[0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xCA, 0x00, 0x88, 0xFF, 0x16, 0x7E, 0x4A, 0xB1, 0x2C, 0xE0, 0xF0],
			[0xFF, 0xFF, 0x00, 0x00, 0xFF, 0x1F, 0x00, 0x88, 0xFF, 0xBB, 0x89, 0xD1, 0x4B, 0x0B, 0xD9, 0x9A],
			[0xFF, 0x00, 0x00, 0x00, 0xFF, 0x63, 0x00, 0x88, 0xFF, 0x47, 0x4F, 0xCC, 0x53, 0xDE, 0xAB, 0x36],
			[0x00, 0x00, 0x00, 0x00, 0xFF, 0x1F, 0x00, 0x88, 0xFF, 0xBB, 0x89, 0xD1, 0x4B, 0x0B, 0xD9, 0x9A],
			#Up to 1024 entries total.
		]*(1024//5+1)*2) #Make it 1024 entries, then double so we can slice 1024 out at any point.
		
		allMockFrameData = ([
			[0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0xFF],
			[0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x20, 0x30, 0x20, 0x10, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF],
			[0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x80, 0xB0, 0x80, 0x40, 0x00, 0x00, 0xFF, 0x00, 0x00, 0xFF],
			[0xFF, 0x00, 0x00, 0x00, 0x00, 0x10, 0x20, 0x30, 0x20, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF],
			[0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF],
			#Up to 1024 entries total.
		]*(1024//5+1)*2) #Make it 1024 entries, then double so we can slice 1024 out at any point.
		
		frameData = allMockFrameData[(startFrame):(1024)-((startFrame-3+1))] #Mock.
		
		return Reply({
			"startFrame": startFrame, #We may have got a request for frame 0, but no longer have the data. In that case, this will be the first frame we do have.
			"endFrame": startFrame + len(frameData), #Number of frames of data being returned.
			"heatmap": QByteArray(bytearray([byte for line in frameData for byte in line])), #The (mock) data being returned. Inefficient, but whatever. Also, what the _heck_, list comprehension syntax.
		})
	
	
	@action('set')
	@pyqtSlot('QVariantList')
	def saveRegions(self, regions: List[Dict[str, Union[int, str, Dict[str, int]]]]) -> None:
		"""Save video clips to disk or network.
			
			Accepts a list of regions, returns a list of statuses.
			
			Args:
				Regions: [{
					"id": str,
					"start": int,
					"end": int,
					"path": str,
					"filename": str, #pertent-escaped filename template? We need something where we can specify what format to put, say, frame numbers and other metadata into the .tiff or .mp4 or whatever file names in.
					"format": { #Optional, these values should have sane defaults if not specified.
						'fps': float, #default 30? or 60?
						'bpp': float,
						'maxBitrate': float,
						'encoding': str, #defaults to h264
						"h264Profile": str if encoding = 'h264', #optional otherwise and ignored
						"h264Level": str if encoding = 'h264',
					},
				}]
			
			Emitted Signals:
				"regionSaving", region id: str, progress: float
					Saving progress for each region. Will always emit
					with at least 0.0 at the start and 1.0 at the end.
				"regionSavingError", region id: str, error: str
					Emitted when a region can't be saved. 😞
				"regionSavingError", error: str
					Emitted when the regions can't be saved.
				"regionSavingCancelled"
					Emitted when the save is cancelled.
				"allRegionsSaved"
					Emitted when all regions have been saved or
					have errored out. Not emitted if cancelled.
			
			Behaviour Notes:
				Camera state will be set to 'saving' and restored upon
				completion. To cancel the save, set the camera state
				to anything other than 'saving'.
				The API remains responsive during the save duration.
			
			Design Notes:
				This function has no return value because the API
				cannot defer returning from a function while still
				processing other function calls, such as 'cancel
				saving'. To get around this, this function returns
				events as emitted signals.
		"""
		
		def setPlaybackFrame(frame):
			"""Dumb hack to assign inside a lambda. No := yet."""
			state.playbackFrame = frame
		
		if state.videoState == 'saving':
			#What should we do if video is already saving? Emit an error?
			#Add the new files to the list of files to be saved?
			self.emitSignal("regionSavingError", "already saving regions")
			return
		
		print(f'saving {len(regions)} region(s)')
		
		self.previousVideoState = state.videoState
		state.videoState = 'saving'
		self.emitControlSignal('videoState')
		
		time = 0
		savedRegions = 0
		for region in regions:
			if region['start'] >= region['end']:
				self.emitSignal('regionSavingError', region['id'],
					f"Region to save must start before it ends. (start={region['start']} >= end={region['end']})" )
				continue
			
			name = ( #Sub in data.
				region['filename']
				.replace(r'%START FRAME%', '{:07d}'.format(region['start']))
				.replace(r'%END FRAME%', '{:07d}'.format(region['end']))
			)
			filename = Path(region['path']) / name
			
			delay(self, time, lambda filename=filename: 
				print('saving', filename)
			)
			
			regionLength = region['end'] - region['start']
			framerate = 30 #virtual
			saveRate = 2000//framerate #fps value
			for frame in range(0, regionLength, saveRate):
				delay(self, time, lambda region=region, frame=frame, regionLength=regionLength: (
					self.emitSignal("regionSaving", region['id'], frame/regionLength),
					setPlaybackFrame(region['start'] + frame),
					self.emitControlSignal('playbackFrame'),
				))
				time += 1000//framerate #emit update once per 16-ms frame
			delay(self, time, lambda region=region: 
				self.emitSignal("regionSaving", region['id'], 1.0)
			)
			
			savedRegions += 1
		
		delay(self, time, lambda: 
			self.emitSignal("allRegionsSaved")
		)
		
		state.videoState = self.previousVideoState
		self.emitControlSignal('videoState')
		
	
	@action('set')
	@pyqtSlot(str)
	def formatStorage(self, device):
		"""Reformat the block device for video saving.
			
			See the gettable "externalStorage" property for a list of
			mounted external storage partitions. Each partition has a
			device associated with it. Formatting the device will
			coalesce and erase all existing partitions and files."""
		
		print(f"MOCK: Formatting device {device}…", end='', flush=True)
		sleep(2)
		print(" done.")
	
	@action('set')
	@pyqtSlot(str)
	def unmount(self, path):
		"""Unmount the partition mounted at path.
			
			See the gettable "externalStorage" property for a list of
			mounted external storage partitions. To remount a device,
			either reinsert it or SSH into the camera and use the
			mount command. (See "man mount" for more details.)"""
		
		print(f"MOCK: Unmounting {path}.")
	
	@action('get')
	@pyqtSlot(result="QVariantMap")
	def df(self, ):
		"""Run the df linux command, and return the output.
			
			Basically, returns a string with information about each partition.
			Forms a nice little table if printed with a fixed-width font. See
			"man df" for more details."""
		
		return Reply(removeWhitespace("""
			NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
			mmcblk0     179:0    0   7.4G  0 disk
			|-mmcblk0p1 179:1    0  39.2M  0 part /boot
			`-mmcblk0p2 179:2    0   7.4G  0 part /
		"""))
	
	
	@action('set')
	@pyqtSlot(result="QVariantMap")
	@pyqtSlot("QVariantMap", result="QVariantMap")
	def testNetworkStorageCredentials(self, config={}):
		"""Check the remote file share works.
			
			Returns an error message upon failure, or an empty string
			on success.
			
			Accepts one map parameter, config, which may contain
				- networkStorageAddress: str
				- networkStorageUsername: str
				- networkStoragePassword: str
			each overriding the API value of the same name."""
			
		
		
		print("MOCK: Checking network storage…", end='', flush=True)
		sleep(3)
		print(" ok.")
		return Reply('')




if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control_mock'):
	sys.stderr.write(f"Could not register control service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	raise Exception("D-Bus Setup Error")

controlAPI = ControlAPIMock() #This absolutely, positively can't be inlined or it throws error "No such object path ...". Possibly, this is because a live reference must be kept so GC doesn't eat it?
QDBusConnection.systemBus().registerObject('/com/krontech/chronos/control_mock', controlAPI, QDBusConnection.ExportAllSlots)


#Launch the API if not imported as a library.
if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	import signal
	
	app = QCoreApplication(sys.argv)
	
	#Quit on ctrl-c.
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	print("Running control api mock.")
	sys.exit(app.exec_())