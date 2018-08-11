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


#Pending callbacks is used by state callbacks to queue long-running or multi
#arg tasks such as changeRecordingResolution. This is so a call to set which
#contains x/y/w/h of a new camera resolution only actually resets the camera
#video pipeline once. Each function which appears in the list is called only
#once, after all values have been set.
pendingCallbacks = []


def changeRecordingResolution(state):
	print(f'Mock: changing recording resolution to xywh {recordingHoffset} {recordingVoffset} {recordingHRes} {recordingVRes}.')


def notifyExposureChange(state):
	print('TODO: Notify exposure change.')
	#self.emitControlSignal('maxExposureNs', 7e8) # Example.
	#self.emitControlSignal('minExposureNs', 3e2)


##############################################
#    Set up mock dbus interface provider.    #
##############################################

class State():
	#Invariant data about the camera.
	cameraModel = "Mock Camera 1.4"
	cameraApiVersion = 1.0
	cameraFpgaVersion = 3.14
	cameraMemoryGB = 160
	cameraSerial = "Captain Crunch"
	sensorName = "acme9001"
	sensorHMax = 1920
	sensorVMax = 1080
	sensorHMin = 256
	sensorVMin = 64
	sensorHIncrement = 2
	sensorVIncrement = 32
	sensorPixelRate = 1920 * 1080 * 1000
	sensorPixelFormat = "BYR2"
	sensorFramerateMax = 1000
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
	
	_recordingHoffset = 800 #rebuilds video pipeline
	
	
	@property
	def recordingHoffset(self): #rebuilds video pipeline
		return self._recordingHoffset
	
	@recordingHoffset.setter
	def recordingHoffset(self, value):
		global pendingCallbacks
		self._recordingHoffset = value
		pendingCallbacks += [changeRecordingResolution]
	
	_recordingVoffset = 480
	
	
	@property
	def recordingVoffset(self):
		return self._recordingVoffset
	
	@recordingVoffset.setter
	def recordingVoffset(self, value):
		global pendingCallbacks
		self._recordingVoffset = value
		pendingCallbacks += [changeRecordingResolution]
	
	recordingAnalogGain = 2 #doesn't rebuild video pipeline
	
	recordingExposureNs = int(8.5e8) #These don't have to have the pipeline torn down, so they don't need the hack where we set video settings atomically.
	recordingPeriodNs = int(4e4)
	
	currentVideoState = 'viwefinder' #eg, 'viewfinder', 'playback', etc.
	currentCameraState = 'normal' #Can also be 'saving' or 'recording'. When saving, the API is unresponsive?
	focusPeakingColor = 0x0000ff #currently presented as red, blue, green, alpha. - 0x000000 is off
	focusPeakingIntensity = 0.5 #1=max, 0=off
	zebraStripesEnabled = False
	connectionTime = "2018-06-19T02:05:52.664Z" #To use this, add however many seconds ago the request was made. Time should pass roughly the same for the camera as for the client.
	disableRingBuffer = False #In segmented mode, disable overwriting earlier recorded ring buffer segments. DDR 2018-06-19: Loial figures this was fixed, but neither of us know why it's hidden in the old UI.
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
	
	overlayIdentifier = 0x55
	overlayVersion = "1.1"
	
	overlayTextbox0Content = 'textbox 0 sample text'
	overlayTextbox0Font = list(b'<binary font data here>')
	overlayTextbox0Colour = 0xFFFFFF20 #RGBA
	overlayTextbox0X = 0x0008
	overlayTextbox0Y = 0x0010
	overlayTextbox0W = 0x02D0
	overlayTextbox0H = 0x0028
	overlayTextbox0OffsetX = 0x08
	overlayTextbox0OffsetY = 0x08
	
	overlayTextbox1Content = 'textbox 1 sample text'
	overlayTextbox1Font = list(b'<binary data here>')
	overlayTextbox1Colour = 0xFFFFFF20 #RGBA
	overlayTextbox1X = 0x0110
	overlayTextbox1Y = 0x03D8
	overlayTextbox1W = 0x0320
	overlayTextbox1H = 0x0028
	overlayTextbox1OffsetX = 0x08
	overlayTextbox1OffsetY = 0x08
	
	overlayWatermarkColour = 0x20202020 #RGBA
	overlayWatermarkX = 0x0008
	overlayWatermarkY = 0x02F8
	
	overlayRGBImage = list(b'<binary data here>')
	overlayRGBLogoPalette = list(b'<binary LUT here>')
	overlayRGBImageX = 0x0190
	overlayRGBImageY = 0x0258
	overlayRGBImageWidth = 0x0080
	overlayRGBImageHeight = 0x0080
		
	

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
		
	@pyqtSlot(result='QVariantMap')
	def available_keys(self):
		return [i for i in dir(state) if i[0] != '_']
			




if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control.mock'):
	sys.stderr.write(f"Could not register control service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	sys.exit(2)

controlMock = ControlMock() #This absolutely, positively can't be inlined or it throws error "No such object path '/'".
QDBusConnection.systemBus().registerObject('/', controlMock, QDBusConnection.ExportAllSlots)

if not QDBusConnection.systemBus().registerService('com.krontech.chronos.video.mock'):
	sys.stderr.write(f"Could not register video service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	sys.exit(2)

videoMock = ControlMock() #This absolutely, positively can't be inlined or it throws error "No such object path '/'".
QDBusConnection.systemBus().registerObject('/', videoMock, QDBusConnection.ExportAllSlots)




#######################
#    Use the mock.    #
#######################

cameraControlAPI = QDBusInterface(
	'com.krontech.chronos.control.mock', #Service
	'/', #Path
	'', #Interface
	QDBusConnection.systemBus() )
cameraVideoAPI = QDBusInterface(
	'com.krontech.chronos.video.mock', #Service
	'/', #Path
	'', #Interface
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
	
	msg = QDBusReply(cameraControlAPI.call(*args, **kwargs))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()


def get(keyOrKeys):
	"""Call the camera control DBus get method.
		
		Accepts str or [str].
		
		Returns value or [value], relatively.
	"""
	
	keyList = [keyOrKeys] if isinstance(keyOrKeys, str) else keyOrKeys
	
	msg = QDBusReply(cameraControlAPI.call('get', keyList))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()[keyOrKeys] if isinstance(keyOrKeys, str) else msg.value()


def set(values):
	"""Call the camera control DBus set method. Accepts {str: value}."""
	
	msg = QDBusReply(cameraControlAPI.call('set', values))
	if not msg.isValid():
		raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	return msg.value()





# State for observe().
_camState = control('get', [i for i in dir(state) if i[0] != '_'])
if(not _camState):
	raise Exception("Cache failed to populate. This indicates the get call is not working.")

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
	
	pass


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
	"""
	
	if not hasattr(callback, '_isSilencedCallback'):
		raise CallbackNotSilenced(f"{callback} must consider silencing. Decorate with @silenceCallbacks(callback_name, …).")
	
	callback(_camState[name])
	QDBusConnection.systemBus().connect('com.krontech.chronos.control.mock', '/', '',
		name, callback)


def observe_future_only(name: str, callback: Callable[[Any], None]) -> None:
	"""Like `observe`, but without the initial callback when observing.
	
		Useful when `observe`ing a derived value, which observe can't deal with yet.
	"""
	
	if not hasattr(callback, '_isSilencedCallback'):
		raise CallbackNotSilenced(f"{callback} must consider silencing. Decorate with @silenceCallbacks(callback_name, …).")
	
	QDBusConnection.systemBus().connect('com.krontech.chronos.control.mock', '/', '',
		name, callback)



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



# Only export the functions we will use. Keep it simple. (This can be complicated later as the need arises.)
__all__ = ['control', 'video', 'observe'] #This doesn't work. Why?


if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	app = QCoreApplication(sys.argv)
	
	print("Self-test: echo service")
	print(f"min recording period: {control('get_timing_limits')['tMinPeriod']}")
	print("Self-test passed. Python mock API is running.")
	
	sys.exit(app.exec_())