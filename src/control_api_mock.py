"""Mock for api.py. Allows easier development & testing of the QT interface.

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
import random
from debugger import *; dbg

from PyQt5.QtCore import pyqtSlot, QObject, QTimer
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply, QDBusMessage, QDBusError
from typing import Callable, Any


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)





########################
#    Pure Functions    #
########################


def resolution_is_valid(hOffset: int, vOffset: int, hRes: int, vRes: int):
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


def framerate_for_resolution(hRes: int, vRes: int):
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
pendingCallbacks = []


def changeRecordingResolution(state):
	print(f'Mock: changing recording resolution to xywh {recordingHOffset} {recordingVOffset} {recordingHRes} {recordingVRes}.')


def notifyExposureChange(state):
	print('TODO: Notify exposure change.')
	#self.emitControlSignal('maxExposureNs', 7e8) # Example.
	#self.emitControlSignal('minExposureNs', 3e2)



#######################################
#    Mock D-Bus Interface Provider    #
#######################################

class State():
	#Invariant data about the camera.
	cameraModel = "Mock Camera 1.4"
	cameraApiVersion = '0.1.0'
	cameraFpgaVersion = '3.14'
	cameraMemoryGB = 16.
	cameraSerial = "Captain Crunch"
	sensorName = "acme9001"
	sensorHMax = 1920
	sensorHMin = 256
	sensorVMax = 1080
	sensorVMin = 64
	sensorHIncrement = 2
	sensorVIncrement = 32
	sensorPixelRate = 1920 * 1080 * 1000
	sensorPixelFormat = "BYR2" #Or "y12" for mono models.
	sensorRecordsColour = True
	sensorFramerate = 1000
	sensorQuantizeTimingNs = 250
	sensorMinExposureNs = int(1e3)
	sensorMaxExposureNs = int(1e9)
	sensorMaxShutterAngle = 330
	timingMaxPeriod = sys.maxsize
	
	@property
	def timingMinPeriod(self):
		return (state.recordingHRes * state.recordingVRes * int(1e9)) / state.sensorPixelRate
	
	timingMinExposureNs = sensorMinExposureNs
	timingMaxExposureNs = sensorMaxExposureNs
	timingExposureDelayNs = 1000
	timingMaxShutterAngle = 330
	timingQuantization = 1e9 / sensorQuantizeTimingNs
	
	@property
	def commonlySupportedResolutions(self): 
		return [{
			'hRes': x, 
			'vRes': y, 
			'framerate': framerate_for_resolution(x, y),
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
	
	#Camera state.
	externallyPowered = True
	batteryCharge = 1. #0. to 1. inclusive
	
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
		pendingCallbacks += [changeRecordingResolution, notifyExposureChange]
	
	_recordingVRes = 300 
	
	
	@property
	def recordingVRes(self): 
		return self._recordingVRes
	
	@recordingVRes.setter
	def recordingVRes(self, value):
		global pendingCallbacks
		self._recordingVRes = value
		pendingCallbacks += [changeRecordingResolution, notifyExposureChange]
	
	_recordingHOffset = 800 #rebuilds video pipeline
	
	
	@property
	def recordingHOffset(self): #rebuilds video pipeline
		return self._recordingHOffset
	
	@recordingHOffset.setter
	def recordingHOffset(self, value):
		global pendingCallbacks
		self._recordingHOffset = value
		pendingCallbacks += [changeRecordingResolution]
	
	_recordingVOffset = 480
	
	
	@property
	def recordingVOffset(self):
		return self._recordingVOffset
	
	@recordingVOffset.setter
	def recordingVOffset(self, value):
		global pendingCallbacks
		self._recordingVOffset = value
		pendingCallbacks += [changeRecordingResolution]
	
	recordingAnalogGain = 2 #doesn't rebuild video pipeline
	
	recordingExposureNs = int(8.5e8) #These don't have to have the pipeline torn down, so they don't need the hack where we set video settings atomically.
	recordingPeriodNs = int(4e4) #I'm assuming this is how long each frame is exposed for? And that there's no delay between exposures?
	
	currentCameraState = 'normal' #Can also be 'saving' or 'recording'. When saving, the API is unresponsive?
	currentVideoState = 'viwefinder' #eg, 'viewfinder', 'playback', etc.
	focusPeakingColor = 0x0000ff #currently presented as red, green, blue, alpha (RGBA). 0x000000 is off
	zebraStripesEnabled = False
	disableOverwritingRingBuffer = False #In segmented mode, disable overwriting earlier recorded ring buffer segments. DDR 2018-06-19: Loial figures this was fixed, but neither of us know why it's hidden in the old UI.
	recordedSegments = [{ #Each entry in this list a segment of recorded video. Although currently resolution/framerate is always the same having it in this data will make it easier to fix this in the future if we do.
		"start": 0,
		"end": 1000,
		"hres": 200,
		"vres": 300,
		"id": "ldPxTT5R",
	}]
	whiteBalance = [1., 1., 1.]
	triggerDelayNs = int(1e9)
	
	triggerConfiguration = { #read/write, what the triggers do
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
	}
	
	@property
	def triggerCapabilities(self): #read, what the triggers are capable of
		return {
			"trig1": {                     # id
				"name": "Trigger 1 (BNC)", # full name (human-readable label)
				"label": "TRIG1",          # short name (as printed on the case)
				"thresholdMinV": 0.,
				"thresholdMaxV": 7.2,
				"pullup1ma": True,
				"pullup20ma": True,
				"outputCapable": True,
			},
			"trig2": {
				"name": "Trigger 2",
				"label": "TRIG2",
				"thresholdMinV": 0.,
				"thresholdMaxV": 7.2,
				"pullup1ma": False,
				"pullup20ma": True,
				"outputCapable": True,
			},
			"trig3": {
				"name": "Trigger 3 (isolated)",
				"label": "TRIG3",
				"thresholdMinV": 0.,
				"thresholdMaxV": 7.2,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
			},
			"~a1": { #DDR 2018-06-18: I don't know what the analog input settings will be like.
				"name": "Analog 1",
				"label": "~A1",
				"thresholdMinV": 0.,
				"thresholdMaxV": 7.2,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
			},
			"~a2": {
				"name": "Analog 2",
				"label": "~A2",
				"thresholdMinV": 0.,
				"thresholdMaxV": 7.2,
				"pullup1ma": False,
				"pullup20ma": False,
				"outputCapable": False,
			},
		}
	
	@property
	def triggers(self):
		return list(self.triggerCapabilities.keys())
	
	@property
	def triggerState(self):
		return {
			"trig1": {
				"active": random.choice((True, False)), #such modelling, so sophisticated 🖏 
				"voltage": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"trig2": {
				"active": random.choice((True, False)),
				"voltage": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"trig3": {
				"active": random.choice((True, False)),
				"voltage": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"~a1": {
				"active": random.choice((True, False)),
				"voltage": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
			"~a2": {
				"active": random.choice((True, False)),
				"voltage": random.choice((2.45, 2.50, 2.50, 2.50, 2.50, 4.11, 4.12))
			},
		}
	
	#Overlay has moved to Video API
	#
	#overlayVersion = "1.1"
	#
	#overlayTextbox0Content = 'textbox 0 sample text'
	#overlayTextbox0Font = list(b'<binary font data here>')
	#overlayTextbox0Colour = 0xFFFFFF20 #RGBA
	#overlayTextbox0X = 0x0008
	#overlayTextbox0Y = 0x0010
	#overlayTextbox0W = 0x02D0
	#overlayTextbox0H = 0x0028
	#overlayTextbox0OffsetX = 0x08
	#overlayTextbox0OffsetY = 0x08
	#
	#overlayTextbox1Content = 'textbox 1 sample text'
	#overlayTextbox1Font = list(b'<binary data here>')
	#overlayTextbox1Colour = 0xFFFFFF20 #RGBA
	#overlayTextbox1X = 0x0110
	#overlayTextbox1Y = 0x03D8
	#overlayTextbox1W = 0x0320
	#overlayTextbox1H = 0x0028
	#overlayTextbox1OffsetX = 0x08
	#overlayTextbox1OffsetY = 0x08
	#
	#overlayChronosWatermarkColour = 0x20202020 #RGBA
	#overlayChronosWatermarkX = 0x0008
	#overlayChronosWatermarkY = 0x02F8
	#
	#overlayRGBImage = list(b'<binary data here>')
	#overlayRGBLogoPalette = list(b'<binary LUT here>')
	#overlayRGBImageX = 0x0190
	#overlayRGBImageY = 0x0258
	#overlayRGBImageWidth = 0x0080
	#overlayRGBImageHeight = 0x0080
		
	

state = State()


class ControlMock(QObject):
	def __init__(self):
		super(ControlMock, self).__init__()
		
		# Inject some fake update events.
		def test1():
			state.recordingExposureNs = int(8e8)
			self.emitControlSignal('recordingExposureNs')
			
		self._timer1 = QTimer()
		self._timer1.timeout.connect(test1)
		self._timer1.setSingleShot(True)
		self._timer1.start(1000) #ms
		
		def test2():
			state.recordingExposureNs = int(2e8)
			self.emitControlSignal('recordingExposureNs')
			
		self._timer2 = QTimer()
		self._timer2.timeout.connect(test2)
		self._timer2.setSingleShot(True)
		self._timer2.start(2000) #ms
		
		def test3():
			state.recordingExposureNs = int(8.5e8)
			self.emitControlSignal('recordingExposureNs')
			
		self._timer3 = QTimer()
		self._timer3.timeout.connect(test3)
		self._timer3.setSingleShot(True)
		self._timer3.start(3000) #ms
	
	
	def emitControlSignal(self, name, value=None):
		"""Emit an update signal, usually for indicating a value has changed."""
		signal = QDBusMessage.createSignal('/', 'com.krontech.chronos.control.mock', name)
		signal << getattr(state, name) if value is None else value
		QDBusConnection.systemBus().send(signal)
	
	
	@pyqtSlot(QDBusMessage, result='QVariantMap')
	def get(self, msg):
		keys = msg.arguments()[0]
		retval = {}
		
		for key in keys:
			if key[0] is '_' or not hasattr(state, key): # Don't allow querying of private variables.
				#QDBusMessage.createErrorReply does not exist in PyQt5, and QDBusMessage.errorReply can't be sent.
				return print("D-BUS ERROR", QDBusError.UnknownProperty, f"The value '{key}' is not known.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
			
			retval[key] = getattr(state, key)
		
		return retval
	
	@pyqtSlot('QVariantMap')
	def set(self, data):
		# Check all errors first to avoid partially applying an update.
		for key, value in data.items():
			if key[0] is '_' or not hasattr(state, key):  # Don't allow setting of private variables.
				# return self.sendError('unknownValue', f"The value '{key}' is not known.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
				return print("D-BUS ERROR", QDBusError.UnknownProperty, f"The value '{key}' is not known.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")
			if not isinstance(value, type(getattr(state, key))):
				return print("D-BUS ERROR", QDBusError.InvalidSignature, f"Can not set '{key}' to {value}.\n(Previously {getattr(state, key)}.) Expected {type(getattr(state, key))}, got {type(value)}.")
		
		# Set only changed variables. Changing can be quite involved, such as with recordingHRes.
		for key, value in data.items():
			if getattr(state, key) != value:
				setattr(state, key, value)
				self.emitControlSignal(key)
				print(f"updated {key} to {value}")
				
		
		#Call each callback only once. For long-running callbacks ior multi-arg tasks.
		global pendingCallbacks
		[cb(_state) for cb in {cb for cb in pendingCallbacks}]
		pendingCallbacks = []
	
	@pyqtSlot()
	def power_down(self):
		print('powering down camera…')
		print('aborted, mock will not shut down machine')
		
	@pyqtSlot(result=list)
	def available_keys(self):
		return [i for i in dir(state) if i[0] != '_']
		
	@pyqtSlot(int, int, result=int)
	def framerate_for_resolution(self, hRes: int, vRes: int):
		return framerate_for_resolution(hRes, vRes)
	
	
	@pyqtSlot(result=bool)
	def resolution_is_valid(self, hOffset: int, vOffset: int, hRes: int, vRes: int): #xywh px
		return resolution_is_valid(hOffset, vOffset, hRes, vRes)