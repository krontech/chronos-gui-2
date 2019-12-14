# -*- coding: future_fstrings -*-

"""Interface for the control api d-bus service."""

from typing import Callable, Any, Dict
import sys, os
import subprocess
from time import perf_counter
from difflib import get_close_matches
from ipaddress import IPv4Address, IPv6Address, AddressValueError
from collections import defaultdict

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply, QDBusPendingCallWatcher, QDBusPendingReply

from chronosGui2.debugger import *; dbg
from chronosGui2 import delay
import logging; log = logging.getLogger('Chronos.api')

#Mock out the old API; use production for this one so we can switch over piecemeal.
USE_MOCK = os.environ.get('USE_CHRONOS_API_MOCK') in ('always', 'gui')
API_INTERCALL_DELAY = 0
API_SLOW_WARN_MS = 100
API_TIMEOUT_MS = 5000

if USE_MOCK: #Resource accquisition is initialisation, here, so importing starts the mocks.
	log.warn(f"Using API mocks. ($USE_CHRONOS_API_MOCK={os.environ.get('USE_CHRONOS_API_MOCK')})")
	import control_api_mock, video_api_mock; control_api_mock, video_api_mock

class apiSingleton(type):
	"""Metaclass used to ensure only one D-Bus API class is instantiated"""
	def __init__(cls, name, bases, attrs, *kwargs):
		super().__init__(name, bases, attrs)
		cls._instance = None
	
	def __call__(cls, *args, **kwargs):
		if cls._instance is None:
			cls._instance = super().__call__(*args, **kwargs)
		return cls._instance

class apiBase():
	"""Call the D-Bus camera APIs, asynchronously.
		
		Methods:
			- call(function[, arg1[ ,arg2[, ...]]])
				Call the remote function.
			- get([value[, ...]])
				Get the named values from the API.
			- set({key: value[, ...]}])
				Set the named values in the API.
		
		All methods return an A* promise-like, in that you use
		`.then(cb(value))` and `.catch(cb(error))` to get the results
		of calling the function.
	"""
	def __init__(self, service, path, interface="", bus=QDBusConnection.systemBus()):
		if not QDBusConnection.systemBus().isConnected():
			log.error("Can not connect to D-Bus. Is D-Bus itself running?")
			raise Exception("D-Bus Setup Error")
		
		self.iface = QDBusInterface(service, path, interface, bus)
		
		log.info("Connected to D-Bus %s API at %s", type(self).__name__, self.iface.path())

		# Check for errors.
		if not self.iface.isValid():
			# Otherwise, an error occured.
			log.error("Can not connect to %s D-Bus API at %s. (%s: %s)",
				type(self).__name__, self.iface.service(),
				self.iface.lastError().name(),
				self.iface.lastError().message())
		else:
			self.iface.setTimeout(API_TIMEOUT_MS)

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


class video(apiBase, metaclass=apiSingleton):
	"""Call the D-Bus video API, asynchronously.
		
		Methods:
			- call(function[, arg1[ ,arg2[, ...]]])
				Call the remote function.
			- get([value[, ...]])
				Get the named values from the API.
			- set({key: value[, ...]}])
				Set the named values in the API.
		
		All methods return an A* promise-like, in that you use
		`.then(cb(value))` and `.catch(cb(error))` to get the results
		of calling the function.
	"""

	def __init__(self):
		super().__init__(
			f"ca.krontech.chronos.{'video_mock' if USE_MOCK else 'video'}", # Service
			f"/ca/krontech/chronos/{'video_mock' if USE_MOCK else 'video'}" # Path
		)
	
	_videoEnqueuedCalls = []
	_videoCallInProgress = False
	_activeCall = None
	
	@staticmethod
	def _enqueueCallback(pendingCall, coalesce: bool=True): #pendingCall is video.call
		"""Enqueue callback. Squash and elide calls to set for efficiency."""
		
		#Step 1: Will this call actually do anything? Elide it if not.
		anticipitoryUpdates = False #Emit update signals before sending the update to the API. Results in faster UI updates but poorer framerate.
		if coalesce and pendingCall._args[0] == 'set':
			#Elide this call if it would not change known state.
			hasNewInformation = False
			newItems = pendingCall._args[1].items()
			for key, value in newItems:
				if _camState[key] != value:
					hasNewInformation = True
					if not anticipitoryUpdates:
						break
					#Update known cam state in advance of state transition.
					log.info(f'Anticipating {key} → {value}.')
					_camState[key] = value
					for callback in apiValues._callbacks[key]:
						callback(value)
			if not hasNewInformation:
				return
		
		if coalesce and pendingCall._args[0] == 'playback':
			#Always merge playback states.
			#Take the playback state already enqueued, {}, and overlay the current playback state. (so, {a:1, b:1} + {b:2} = {a:1, b:2})
			assert type(pendingCall._args[1]) is dict, f"playback() takes a {{key:value}} dict, got {pendingCall._args[1]} of type {type(pendingCall._args[1])}."
			existingParams = [call._args[1] for call in video._videoEnqueuedCalls if call._args[0] == 'playback']
			if not existingParams:
				video._videoEnqueuedCalls += [pendingCall]
			else:
				#Update the parameters of the next playback call instead of enqueueing a new call.
				for k, v in pendingCall._args[1].items():
					existingParams[-1][k] = v
				
			return
		
		#Step 2: Is there already a set call pending? (Note that non-set calls act as set barriers; two sets won't get coalesced if a non-set call is between them.)
		if coalesce and [pendingCall] == video._videoEnqueuedCalls[:1]:
			video._videoEnqueuedCalls[-1] = pendingCall
		else:
			video._videoEnqueuedCalls += [pendingCall]
	
	@staticmethod
	def _startNextCallback():
		"""Check for pending callbacks.
			
			If none are found, simply stop.
			
			Note: Needs to be manually pumped.
		"""
		
		if video._videoEnqueuedCalls:
			video._videoCallInProgress = True
			video._videoEnqueuedCalls.pop(0)._startAsyncCall()
		else:
			video._videoCallInProgress = False
	
	
	class call(QObject):
		"""Call the camera video DBus API. First arg is the function name. Returns a promise.
		
			See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
			See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
			See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
		"""
		
		def __init__(self, *args, immediate=True):
			assert args, "Missing call name."
			
			super().__init__()
			
			self._args = args
			self._thens = []
			self._catches = []
			self._done = False
			self._watcherHolder = None
			self.performance = {
				'enqueued': perf_counter(),
				'started': 0.,
				'finished': 0.,
				'handled': 0.,
			}
			
			log.debug(f'enquing {self}')
			video._enqueueCallback(self)
			#log.debug(f'current video queue: {video._videoEnqueuedCalls}')
			if not video._videoCallInProgress:
				#Don't start multiple callbacks at once, the most recent one will block.
				video._startNextCallback()
		
		def __eq__(self, other):
			# If a video call sets the same keys as another
			# video call, then it is equal to itself and can
			# be deduplicated as all sets of the same values
			# have the same side effects. (ie, Slider no go
			# fast if me no drop redundant call.)
			#   –DDR 2019-05-14
			return (
				'set' == self._args[0] == other._args[0]
				and self._args[1].keys() == other._args[1].keys()
			)
		
		def __repr__(self):
			return f'''video.call({', '.join([repr(x) for x in self._args])})'''
			
		
		def _startAsyncCall(self):
			log.debug(f'starting async call: {self._args[0]}({self._args[1:]})')
			self.performance['started'] = perf_counter()
			self._watcherHolder = QDBusPendingCallWatcher(
				video().iface.asyncCallWithArgumentList(self._args[0], self._args[1:])
			)
			self._watcherHolder.finished.connect(self._asyncCallFinished)
			video._activeCall = self
			
		
		def _asyncCallFinished(self, watcher):
			log.debug(f'finished async call: {self}')
			self.performance['finished'] = perf_counter()
			self._done = True
			
			reply = QDBusPendingReply(watcher)
			try:
				if reply.isError():
					if self._catches:
						error = reply.error()
						for catch in self._catches:
							try:
								error = catch(error)
							except Exception as e:
								error = e
					else:
						#This won't do much, but (I'm assuming) most calls simply won't ever fail.
						if reply.error().name() == 'org.freedesktop.DBus.Error.NoReply':
							raise DBusException(f"{self} timed out ({API_TIMEOUT_MS}ms)")
						else:
							raise DBusException("%s: %s" % (reply.error().name(), reply.error().message()))
				else:
					value = reply.value()
					for then in self._thens:
						try:
							value = then(value)
						except Exception as error:
							if self._catches:
								for catch in self._catches:
									try:
										error = catch(error)
									except Exception as e:
										error = e
							else:
								raise e
			except Exception as e:
				raise e
			finally:
				#Wait a little while before starting on the next callback.
				#This makes the UI run much smoother, and usually the lag
				#is covered by the UI updating another few times anyway.
				#Note that because each call still lags a little, this
				#causes a few dropped frames every time the API is called.
				delay(self, API_INTERCALL_DELAY, video._startNextCallback)
				
				self.performance['handled'] = perf_counter()
				if self.performance['finished'] - self.performance['started'] > API_SLOW_WARN_MS / 1000:
					log.warn(
						f'''slow call: {self} took {
							(self.performance['finished'] - self.performance['started'])*1000
						:0.0f}ms/{API_SLOW_WARN_MS}ms. (Total call time was {
							(self.performance['handled'] - self.performance['enqueued'])*1000
						:0.0f}ms.)'''
					)
		
		def then(self, callback):
			assert callable(callback), "video().then() only accepts a single, callable function."
			assert not self._done, "Can't register new then() callback, call has already been resolved."
			self._thens += [callback]
			return self
		
		def catch(self, callback):
			assert callable(callback), "video().then() only accepts a single, callable function."
			assert not self._done, "Can't register new then() callback, call has already been resolved."
			self._catches += [callback]
			return self
	
	def callSync(*args, warnWhenCallIsSlow=True, **kwargs):
		"""Call the camera video DBus API. First arg is the function name.
			
			This is the synchronous version of the call() method. It
			is much slower to call synchronously than asynchronously!
		
			See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
			See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
			See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
		"""
		
		#Unwrap D-Bus errors from message.
		log.debug(f'video.callSync{tuple(args)}')
		
		start = perf_counter()
		msg = QDBusReply(video().iface.call(*args, **kwargs))
		end = perf_counter()
		if warnWhenCallIsSlow and (end - start > API_SLOW_WARN_MS / 1000):
			log.warn(f'slow call: video.callSync{tuple(args)} took {(end-start)*1000:.0f}ms/{API_SLOW_WARN_MS}ms.')
		
		if msg.isValid():
			return msg.value()
		else:
			if msg.error().name() == 'org.freedesktop.DBus.Error.NoReply':
				raise DBusException(f"video.callSync{tuple(args)} timed out ({API_TIMEOUT_MS}ms)")
			else:
				raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))
	
	
	def restart(*_):
		"""Helper method to reboot the video pipeline.
			
			Sometimes calls do not apply until you restart the daemon, although they should.
			Literally every use of this function is a bug.
		"""
		
		os.system('killall -HUP cam-pipeline')


class control(apiBase, metaclass=apiSingleton):
	"""Call the D-Bus control API, asychronously.
		
		Methods:
			- call(function[, arg1[ ,arg2[, ...]]])
				Call the remote function.
			- get([value[, ...]])
				Get the named values from the API.
			- set({key: value[, ...]}])
				Set the named values in the API.
		
		All methods return an A* promise-like, in that you use
		`.then(cb(value))` and `.catch(cb(error))` to get the results
		of calling the function.
	"""
	def __init__(self):
		super().__init__(
			f"ca.krontech.chronos.{'control_mock' if USE_MOCK else 'control'}", #Service
			f"/ca/krontech/chronos/{'control_mock' if USE_MOCK else 'control'}", #Path
		)

	_controlEnqueuedCalls = []
	_controlCallInProgress = False
	_activeCall = None
	
	@staticmethod
	def _enqueueCallback(pendingCall, coalesce: bool=True): #pendingCall is control.call
		"""Enqueue callback. Squash and elide calls to set for efficiency."""
		
		#Step 1: Will this call actually do anything? Elide it if not.
		anticipitoryUpdates = False #Emit update signals before sending the update to the API. Results in faster UI updates but poorer framerate.
		if coalesce and pendingCall._args[0] == 'set':
			#Elide this call if it would not change known state.
			hasNewInformation = False
			newItems = pendingCall._args[1].items()
			for key, value in newItems:
				if _camState[key] != value:
					hasNewInformation = True
					if not anticipitoryUpdates:
						break
					#Update known cam state in advance of state transition.
					log.info(f'Anticipating {key} → {value}.')
					_camState[key] = value
					for callback in apiValues._callbacks[key]:
						callback(value)
			if not hasNewInformation:
				return
		
		#Step 2: Is there already a set call pending? (Note that non-set calls act as set barriers; two sets won't get coalesced if a non-set call is between them.)
		if coalesce and [pendingCall] == control._controlEnqueuedCalls[:1]:
			control._controlEnqueuedCalls[-1] = pendingCall
		else:
			control._controlEnqueuedCalls += [pendingCall]
	
	@staticmethod
	def _startNextCallback():
		"""Check for pending callbacks.
			
			If none are found, simply stop.
			
			Note: Needs to be manually pumped.
		"""
		
		if control._controlEnqueuedCalls:
			control._controlCallInProgress = True
			control._controlEnqueuedCalls.pop(0)._startAsyncCall()
		else:
			control._controlCallInProgress = False
	
	
	class call(QObject):
		"""Call the camera control DBus API. First arg is the function name. Returns a promise.
		
			See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
			See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
			See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
		"""
		
		def __init__(self, *args, immediate=True):
			assert args, "Missing call name."
			
			super().__init__()
			
			self._args = args
			self._thens = []
			self._catches = []
			self._done = False
			self._watcherHolder = None
			self.performance = {
				'enqueued': perf_counter(),
				'started': 0.,
				'finished': 0.,
				'handled': 0.,
			}
			
			log.debug(f'enquing {self}')
			control._enqueueCallback(self)
			#log.debug(f'current control queue: {control._controlEnqueuedCalls}')
			if not control._controlCallInProgress:
				#Don't start multiple callbacks at once, the most recent one will block.
				control._startNextCallback()
		
		def __eq__(self, other):
			# If a control call sets the same keys as another
			# control call, then it is equal to itself and can
			# be deduplicated as all sets of the same values
			# have the same side effects. (ie, Slider no go
			# fast if me no drop redundant call.)
			#   –DDR 2019-05-14
			return (
				'set' == self._args[0] == other._args[0]
				and self._args[1].keys() == other._args[1].keys()
			)
		
		def __repr__(self):
			return f'''control.call({', '.join([repr(x) for x in self._args])})'''
			
		
		def _startAsyncCall(self):
			log.debug(f'starting async call: {self._args[0]}({self._args[1:]})')
			self.performance['started'] = perf_counter()
			self._watcherHolder = QDBusPendingCallWatcher(
				control().iface.asyncCallWithArgumentList(self._args[0], self._args[1:])
			)
			self._watcherHolder.finished.connect(self._asyncCallFinished)
			control._activeCall = self
			
		
		def _asyncCallFinished(self, watcher):
			log.debug(f'finished async call: {self}')
			self.performance['finished'] = perf_counter()
			self._done = True
			
			reply = QDBusPendingReply(watcher)
			try:
				if reply.isError():
					if self._catches:
						error = reply.error()
						for catch in self._catches:
							try:
								error = catch(error)
							except Exception as e:
								error = e
					else:
						#This won't do much, but (I'm assuming) most calls simply won't ever fail.
						if reply.error().name() == 'org.freedesktop.DBus.Error.NoReply':
							raise DBusException(f"{self} timed out ({API_TIMEOUT_MS}ms)")
						else:
							raise DBusException("%s: %s" % (reply.error().name(), reply.error().message()))
				else:
					value = reply.value()
					for then in self._thens:
						try:
							value = then(value)
						except Exception as error:
							if self._catches:
								for catch in self._catches:
									try:
										error = catch(error)
									except Exception as e:
										error = e
							else:
								raise error
			except Exception as e:
				raise e
			finally:
				#Wait a little while before starting on the next callback.
				#This makes the UI run much smoother, and usually the lag
				#is covered by the UI updating another few times anyway.
				#Note that because each call still lags a little, this
				#causes a few dropped frames every time the API is called.
				delay(self, API_INTERCALL_DELAY, control._startNextCallback)
				
				self.performance['handled'] = perf_counter()
				if self.performance['finished'] - self.performance['started'] > API_SLOW_WARN_MS / 1000:
					log.warn(
						f'''slow call: {self} took {
							(self.performance['finished'] - self.performance['started'])*1000
						:0.0f}ms/{API_SLOW_WARN_MS}ms. (Total call time was {
							(self.performance['handled'] - self.performance['enqueued'])*1000
						:0.0f}ms.)'''
					)
		
		def then(self, callback):
			assert callable(callback), "control().then() only accepts a single, callable function."
			assert not self._done, "Can't register new then() callback, call has already been resolved."
			self._thens += [callback]
			return self
		
		def catch(self, callback):
			assert callable(callback), "control().then() only accepts a single, callable function."
			assert not self._done, "Can't register new then() callback, call has already been resolved."
			self._catches += [callback]
			return self
	
	def callSync(*args, warnWhenCallIsSlow=True, **kwargs):
		"""Call the camera control DBus API. First arg is the function name.
			
			This is the synchronous version of the call() method. It
			is much slower to call synchronously than asynchronously!
		
			See http://doc.qt.io/qt-5/qdbusabstractinterface.html#call for details about calling.
			See https://github.com/krontech/chronos-cli/tree/master/src/api for implementation details about the API being called.
			See README.md at https://github.com/krontech/chronos-cli/tree/master/src/daemon for API documentation.
		"""
		
		#Unwrap D-Bus errors from message.
		log.debug(f'control.callSync{tuple(args)}')
		
		start = perf_counter()
		msg = QDBusReply(control().iface.call(*args, **kwargs))
		end = perf_counter()
		if warnWhenCallIsSlow and (end - start > API_SLOW_WARN_MS / 1000):
			log.warn(f'slow call: control.callSync{tuple(args)} took {(end-start)*1000:.0f}ms/{API_SLOW_WARN_MS}ms.')
			
		if msg.isValid():
			return msg.value()
		else:
			if msg.error().name() == 'org.freedesktop.DBus.Error.NoReply':
				raise DBusException(f"control.callSync{tuple(args)} timed out ({API_TIMEOUT_MS}ms)")
			else:
				raise DBusException("%s: %s" % (msg.error().name(), msg.error().message()))

	


def getSync(keyOrKeys):
	"""Call the camera control DBus get method.
	
		Convenience method for `control('get', [value])[0]`.
		
		Accepts key or [key, …], where keys are strings.
		
		Returns value or {key:value, …}, respectively.
		
		See control's `availableKeys` for a list of valid inputs.
	"""
	
	valueList = control.callSync('get',
		[keyOrKeys] if isinstance(keyOrKeys, str) else keyOrKeys )
	return valueList[keyOrKeys] if isinstance(keyOrKeys, str) else valueList

def get(keyOrKeys):
	"""Call the camera control DBus get method.
	
		Convenience method for `control('get', [value])[0]`.
		
		Accepts key or [key, …], where keys are strings.
		
		Returns value or {key:value, …}, respectively.
		
		See control's `availableKeys` for a list of valid inputs.
	"""
	
	return control.call(
		'get', [keyOrKeys] if isinstance(keyOrKeys, str) else keyOrKeys
	).then(lambda valueList:
		valueList[keyOrKeys] if isinstance(keyOrKeys, str) else valueList
	)

def setSync(*args):
	"""Call the camera control DBus set method.
		
		Accepts {str: value, ...} or a key and a value.
		Returns either a map of set values or the set
			value, if the second form was used.
	"""
	
	if len(args) == 1:
		return control.callSync('set', *args)
	elif len(args) == 2:
		return control.callSync('set', {args[0]:args[1]})[args[0]]
	else:
		raise valueError('bad args')



def set(*args):
	"""Call the camera control DBus set method.
		
		Accepts {str: value, ...} or a key and a value.
		Returns either a map of set values or the set
			value, if the second form was used.
	"""
	
	log.debug(f'simple set call: {args}')
	if len(args) == 1:
		return control.call('set', *args)
	elif len(args) == 2:
		return control.call(
			'set', {args[0]:args[1]}
		).then(lambda valueDict: 
			valueDict[args[0]]
		)
	else:
		raise valueError('bad args')





# State cache for observe(), so it doesn't have to query the status of a variable on each subscription.
# Since this often crashes during development, the following line can be run to try getting each variable independently.
#     for key in [k for k in control.callSync('availableKeys') if k not in {'dateTime', 'externalStorage'}]: print('getting', key); control.callSync('get', [key])
__badKeys = {} #set of blacklisted keys - useful for when one is unretrievable during development.
if control().iface.isValid():
	_camState = control.callSync('get', [
		key
		for key in control.callSync('availableKeys')
		if key not in __badKeys
	], warnWhenCallIsSlow=False)
	if(not _camState):
		raise Exception("Cache failed to populate. This indicates the get call is not working.")
	_camState['error'] = '' #Last error is reported inline sometimes.
	
	if 'videoSegments' not in _camState:
		log.warn('videoSegments not found in availableKeys (pychronos/issues/31)')
		_camState['videoSegments'] = []
	if 'videoZoom' not in _camState:
		log.warn('videoZoom not found in availableKeys (pychronos/issues/52)')
		_camState['videoZoom'] = 1
else:
	_camState = {}
_camStateAge = {k:0 for k,v in _camState.items()}

class APIValues(QObject):
	"""Wrapper class for subscribing to API values in the chronos API."""
	
	def __init__(self):
		super(APIValues, self).__init__()
		
		#The .connect call freezes if we don't do this, or if we do this twice.
		QDBusConnection.systemBus().registerObject(
			f"/ca/krontech/chronos/{'control_mock_hack' if USE_MOCK else 'control_hack'}", 
			self,
		)
		
		self._callbacks = {value: [] for value in _camState}
		self._callbacks['all'] = [] #meta, watch everything
		
		QDBusConnection.systemBus().connect(
			f"ca.krontech.chronos.{'control_mock' if USE_MOCK else 'control'}", 
			f"/ca/krontech/chronos/{'control_mock' if USE_MOCK else 'control'}",
			f"",
			'notify', 
			self.__newKeyValue,
		)
	
	def observe(self, key, callback):
		"""Add a function to get called when a value is updated."""
		assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
		assert key in self._callbacks, f"Unknown value, '{key}', to observe.\n\nAvailable keys are: \n{chr(10).join(self._callbacks.keys())}\n\nDid you mean to observe '{(get_close_matches(key, self._callbacks.keys(), n=1) or ['???'])[0]}' instead of '{key}'?\n"
		self._callbacks[key].append(callback)
	
	def unobserve(self, key, callback):
		"""Stop a function from getting called when a value is updated."""
		assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
		self._callbacks[key].remove(callback)
	
	def __newValueIsEnqueued(self, key):
		return True in [
			key in call._args[1]
			for call in control._controlEnqueuedCalls
			if call._args[0] == 'set'
		]
	
	@pyqtSlot('QDBusMessage')
	def __newKeyValue(self, msg):
		"""Update _camState and invoke any  registered observers."""
		newItems = msg.arguments()[0].items()
		log.info(f'Received new information. {msg.arguments()[0] if len(str(msg.arguments()[0])) <= 45 else chr(10)+prettyFormat(msg.arguments()[0])}')
		for key, value in newItems:
			if _camState[key] != value and not self.__newValueIsEnqueued(key):
				_camState[key] = value
				_camStateAge[key] += 1
				for callback in self._callbacks[key]:
					callback(value)
				for callback in self._callbacks['all']:
					callback(key, value)
			else:
				log.info(f'Ignoring {key} → {value}, stale.')
	
	def get(self, key):
		return _camState[key]

apiValues = APIValues()
del APIValues


def observe(name: str, callback: Callable[[Any], None]) -> None:
	"""Observe changes in a state value.
	
		Args:
			name: ID of the state variable. "exposure", "focusPeakingColor", etc.
			callback: Function called when the state updates and upon subscription.
				Called with one parameter, the new value. Called when registered
				and when the value updates.
		
		Note: Some frequently updated values (~> 10/sec) are only available via
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
	
	assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
	apiValues.observe(name, callback)
	callback(apiValues.get(name))


def observe_future_only(name: str, callback: Callable[[Any], None]) -> None:
	"""Like `observe`, but without the initial callback when observing.
	
		Useful when `observe`ing a derived value, which observe can't deal with yet.
	"""
	
	assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
	apiValues.observe(name, callback)


unobserve = apiValues.unobserve



class Signal(QObject):
	def __init__(self):
		super().__init__()
		
		self._signalObservers = {
			'sof': [], #Use lists here to preserve order of callbacks.
			'eof': [],
			'segment': [],
		}
		
		
		#The .connect call freezes if we don't do this, or if we do this twice.
		QDBusConnection.systemBus().registerObject(
			f"/ca/krontech/chronos/{'video_mock_hack' if USE_MOCK else 'video_hack'}", 
			self,
		)
		
		for signal_ in self._signalObservers:
			QDBusConnection.systemBus().connect(
				f"ca.krontech.chronos.{'video_mock' if USE_MOCK else 'video'}", 
				f"/ca/krontech/chronos/{'video_mock' if USE_MOCK else 'video'}",
				f"",
				signal_, 
				getattr(self, f'_{type(self).__name__}__{signal_}')
			)
	
	
	#Sort of a reverse trampoline, needed because callbacks must be decorated.
	@pyqtSlot('QDBusMessage')
	def __sof(self, msg):
		log.debug(f'''video signal: sof ({len(self._signalObservers['sof'])} handlers)''')
		self.__invokeCallbacks('sof', *msg.arguments())
	@pyqtSlot('QDBusMessage')
	def __eof(self, msg):
		log.debug(f'''video signal: eof ({len(self._signalObservers['eof'])} handlers)''')
		self.__invokeCallbacks('eof', *msg.arguments())
	@pyqtSlot('QDBusMessage')
	def __segment(self, msg):
		log.debug(f'''video signal: segment ({len(self._signalObservers['segment'])} handlers)''')
		self.__invokeCallbacks('segment', *msg.arguments())
	
	def __invokeCallbacks(self, signal, data):
		for callback in self._signalObservers[signal]:
			callback(data)
	
	
	def observe(self, signal: str, handler: Callable[[Any], None]) -> None:
		"""Add a function to get called when a D-BUS signal is emitted."""
		assert callable(handler), f"Handler is not callable. (Expected function, got {handler}.)"
		self._signalObservers[signal].append(handler)
	
	def unobserve(self, signal: str, handler: Callable[[Any], None]) -> None:
		"""Stop a function from getting called when a D-BUS signal is emitted."""
		assert callable(handler), f"Handler is not callable. (Expected function, got {handler}.)"
		self._signalObservers[signal].remove(handler)
signal = Signal()
del Signal



##############################
#   Non-Chronos D-Bus APIs   #
##############################

class ExternalPartitions(QObject):
	def __init__(self):
		"""
			Get _partitions, a list of things you can save video to.
			{
				"name": "Testdisk",
				"device": "mmcblk0p1",
				"uuid": "a14d610d-b524-4af2-9a1a-fa3dd1184258",
				"path": bytes("/dev/sda", 'utf8'),
				"size": 1294839100, #bytes, 64-bit positive integer
				"readOnly": False,
				"interface": "usb", #"usb" or "sd"
			}
		"""
		super().__init__()
		self._partitions = []
		
		#observers collection
		self._callbacks = []
		self.uDisks2ObjectManager = QDBusInterface(
			f"org.freedesktop.UDisks2", #Service
			f"/org/freedesktop/UDisks2", #Path
			f"org.freedesktop.DBus.ObjectManager", #Interface
			QDBusConnection.systemBus(),
		)
		self.uDisks2ObjectManager.setTimeout(10) #Set to 1000 after startup period.
		
		#Retry. This doesn't connect the first time, no matter what the time limit is. I don't know why, probably something in the start-on-demand logic.
		if not self.uDisks2ObjectManager.isValid():
			self.uDisks2ObjectManager = QDBusInterface(
				f"org.freedesktop.UDisks2", #Service
				f"/org/freedesktop/UDisks2", #Path
				f"org.freedesktop.DBus.ObjectManager", #Interface
				QDBusConnection.systemBus(),
			)
			self.uDisks2ObjectManager.setTimeout(10)
			
			if not self.uDisks2ObjectManager.isValid():
				log.critical(f"Error: Can not connect to udisks2 at {self.uDisks2ObjectManager.service()}. ({self.uDisks2ObjectManager.lastError().name()}: {self.uDisks2ObjectManager.lastError().message()}) Try running `apt install udisks2`?")
				raise Exception("D-Bus Setup Error")
		
		self.uDisks2ObjectManager.setTimeout(1000)
		
		
		#The .connect call freezes if we don't do this, or if we do this twice.
		#This bug was fixed by Qt 5.11.
		QDBusConnection.systemBus().registerObject(
			f"/org/freedesktop/UDisks2", 
			self,
		)
		
		QDBusConnection.systemBus().connect(
			f"org.freedesktop.UDisks2", #Service
			f"/org/freedesktop/UDisks2", #Path
			f"org.freedesktop.DBus.ObjectManager", #Interface
			'InterfacesAdded', #Signal
			self.__interfacesAddedEvent,
		)
		
		QDBusConnection.systemBus().connect(
			f"org.freedesktop.UDisks2", #Service
			f"/org/freedesktop/UDisks2", #Path
			f"org.freedesktop.DBus.ObjectManager", #Interface
			'InterfacesRemoved', #Signal
			self.__interfacesRemovedEvent,
		)	
		
		for name, data in QDBusReply(self.uDisks2ObjectManager.call('GetManagedObjects')).value().items():
			self.__interfacesAdded(name, data)
	
	def __getitem__(self, i):
		return self._partitions[i]
	
	def __repr__(self):
		#pdb uses repr instad of str (which imo is more appropriate for an interactive debugging session)
		return f'{type(self)} ({self._partitions})'
	
	def observe(self, callback):
		"""Add a function to get called when a volume is mounted or unmounted.
			
			The added function is immediately invoked."""
		
		assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
		self._callbacks += [callback]
		callback(self._partitions)
	
	def unobserve(self, callback):
		"""Stop a function from getting called when a volume is mounted or unmounted."""
		
		assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
		self._callbacks = list(filter(
			lambda existingCallback: existingCallback != callback, 
			self._callbacks ) )
	
	
	@pyqtSlot('QDBusMessage')
	def __interfacesAddedEvent(self, msg):
		self.__interfacesAdded(*msg.arguments())
	
	def __interfacesAdded(self, name, data):
		if 'org.freedesktop.UDisks2.Filesystem' in data:
			#"Now, for each file system which just got mounted, …"
			
			#Filter root, which is mounted on / and /media/mmcblk0p2.
			if len(data['org.freedesktop.UDisks2.Filesystem']['MountPoints']) != 1:
				return
			
			#Filter out whatever gets mounted to /boot.
			if not bytes(data['org.freedesktop.UDisks2.Filesystem']['MountPoints'][0]).startswith(b'/media/'):
				return
			
			log.debug(f"Partition mounted at {bytes(data['org.freedesktop.UDisks2.Filesystem']['MountPoints'][0]).decode('utf-8')}.") #toStdString() doesn't seem to exist, perhaps because we don't have std strings.
			
			self._partitions += [{
				'name': data['org.freedesktop.UDisks2.Block']['IdLabel'],
				'device': name,
				'uuid': data['org.freedesktop.UDisks2.Block']['IdUUID'], #Found at `/dev/disk/by-uuid/`.
				'path': bytes(data['org.freedesktop.UDisks2.Filesystem']['MountPoints'][0])[:-1], #Trim off a null byte at the end, we don't need it in python.
				'size': data['org.freedesktop.UDisks2.Block']['Size'], #number of bytes, 64-bit positive integer
				'readOnly': data['org.freedesktop.UDisks2.Block']['ReadOnly'],
				'interface': 'usb' if True in [b'usb' in symlink for symlink in data['org.freedesktop.UDisks2.Block']['Symlinks']] else 'other', #This data comes in one message earlier, but it would be enough complexity to link the two that it makes more sense to just string match here.
			}]
			for callback in self._callbacks:
				callback(self._partitions)
	
	
	@pyqtSlot('QDBusMessage')
	def __interfacesRemovedEvent(self, msg):
		self.__interfacesRemoved(*msg.arguments())
	
	def __interfacesRemoved(self, name, data):
		if 'org.freedesktop.UDisks2.Partition' == data[0]:
			#"Now, for each file system which just got removed, …"
			self._partitions = list(filter(
				lambda partition: partition["device"] != name, 
				self._partitions ) )
			for callback in self._callbacks:
				callback(self._partitions)
	
	
	def list(self):
		return self._partitions
	
	def usageFor(self, device: str, callback: Callable[[], Dict[str,int]]):
		for partition in self._partitions:
			if partition['device'] == device:
				df = subprocess.Popen(
					['df', partition['path'], '--output=avail,used'], #used+avail != 1k-blocks
					stdout=subprocess.PIPE,
					stderr=subprocess.DEVNULL )
				
				def checkDf(*, timeout):
					exitStatus = df.poll()
					if exitStatus is None: #Still running, check again later.
						#Standard clamped exponential decay. Keeps polling to a reasonable amount, frequent at first then low.
						delay(self, timeout, lambda:
							checkDf(timeout=max(1, timeout*2)) )
					elif exitStatus: #df failure, raise an error
						if exitStatus == 1:
							#When a storage device with multiple partitions is removed,
							#the observer fires once for each partition. This means
							#that, for one partition, the client will issue a spurious
							#call to this function with the stale partition's device.
							log.debug(f'Unknown device {device}.')
							log.debug(f'Known devices are {[p["device"] for p in self._partitions]}.')
						else:
							raise Exception(f'df exited with error {exitStatus}')
					else:
						info = ( #Chop up df command output.
							df.communicate()[0]
							.split(b'\n')[1] #Remove first line, column headings
							.split() #Each output is now in a list.
						)
						callback({
							'available': int(info[0]),
							'used': int(info[1]),
							'total': int(info[0]) + int(info[1]),
						})
				delay(self, 0.20, lambda: #Initial delay, df usually runs in .17s.
					checkDf(timeout=0.05) )
externalPartitions = ExternalPartitions()
del ExternalPartitions



class NetworkInterfaces(QObject):
	def __init__(self):
		"""
			NetworkInterfaces is a list of the plugged-in network connections.
			
			```python
				[{
					"path": b"/org/freedesktop/NetworkManager/Devices/1"
					"name": "Ethernet",
					"address": "192.168.100.166" or "2001:0db8:85a3::8a2e:0370:7334"
				}, {
					...
				}]
			```
			
			You can `networkInterfaces.observe(callback)` to get updates.
			
		"""
		super().__init__()
		self._connections = []
		
		#observers collection
		self._callbacks = []
		self.networkManager = QDBusInterface(
			f"org.freedesktop.NetworkManager", #Service
			f"/org/freedesktop/NetworkManager", #Path
			f"org.freedesktop.NetworkManager", #Interface
			QDBusConnection.systemBus(),
		)
		self.networkManager.setTimeout(10) #Set to 1000 after startup period.
		
		#Retry. This doesn't connect the first time, no matter what the time limit is. I don't know why, probably something in the start-on-demand logic.
		if not self.networkManager.isValid():
			self.networkManager = QDBusInterface(
				f"org.freedesktop.NetworkManager", #Service
				f"/org/freedesktop/NetworkManager", #Path
				f"org.freedesktop.NetworkManager", #Interface
				QDBusConnection.systemBus(),
			)
			self.networkManager.setTimeout(10)
			
			if not self.networkManager.isValid():
				log.critical(f"Error: Can not connect to NetworkManager at {self.networkManager.service()}. ({self.networkManager.lastError().name()}: {self.networkManager.lastError().message()}) Try running `apt install network-manager`?")
				raise Exception("D-Bus Setup Error")
		
		self.networkManager.setTimeout(1000)
		
		
		#The .connect call freezes if we don't do this, or if we do this twice.
		#This bug was fixed by Qt 5.11.
		QDBusConnection.systemBus().registerObject(
			f"/org/freedesktop/NetworkManager", 
			self,
		)
		
		self._acquireInterfacesCall = QDBusPendingCallWatcher(
			self.networkManager.asyncCall('GetDevices')
		)
		self._acquireInterfacesCall.finished.connect(self._acquireInterfaceData)
	def _acquireInterfaceData(self, reply):
		"""Continuation of __init__.
		
			[DDR 2019-11-05] Note: In Qt 5.7, we can't just go
			self._networkInterfaces['Device'].property(), like we could with
			self._networkInterfaces['Device'].call(), because .property()
			doesn't seem to work. afaik, it _should_ work, and the example in
			https://stackoverflow.com/questions/20042995/error-getting-dbus-interface-property-with-qdbusinterface
			which is directly relevant to our situation shows it working. Yet,
			I cannot figure out how to port it to Python. So we do it manually
			with the `'* property interface'`s.
					Note: https://doc.qt.io/archives/qt-5.7/qnetworkinterface.html is
			a thing. Shame it doesn't have notification events.
					Command-line based examples:
			docs: https://developer.gnome.org/NetworkManager/0.9/spec.html
			org.freedesktop.NetworkManager.Device.Wired has ipv4/6 properties
			gdbus introspect --system --dest org.freedesktop.NetworkManager.Device.Wired --object-path /org/freedesktop/NetworkManager/Device/Wired
			
			- Get network interfaces:
				> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager
					- Has ActivateConnection method in org.freedesktop.NetworkManager
					- Has GetDevices method in org.freedesktop.NetworkManager
						> gdbus call --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager --method org.freedesktop.NetworkManager.GetDevices
							- ([objectpath '/org/freedesktop/NetworkManager/Devices/0', '/org/freedesktop/NetworkManager/Devices/1', '/org/freedesktop/NetworkManager/Devices/2', '/org/freedesktop/NetworkManager/Devices/3'],)
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/0
							- This is apparently a network connection - in this case, loopback.
							- Links to IPv4/6 config.
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/1
							- eth0
							- is plugged in?
								- org.freedesktop.NetworkManager.Device.Wired property Carrier
								- [implements g interfaces] Filter org.freedesktop.NetworkManager.GetDevices to get the list of plugged-in interfaces.
							> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/DHCP4Config/0
								- yields org.freedesktop.NetworkManager.DHCP4Config
								- from ip_address' Dhcp4Config property
								- [implements g n lan IPv4 or v6] in properties & PropertiesChanged signal.
							> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/IP6Config/2
								- yields org.freedesktop.NetworkManager.IP6Config
								- from ip_address' Ip6Config property
								- [implements g n g n www IPv4 or v6] in Addresses (first item) & PropertiesChanged signal.
							- has Disconnect method
								- https://developer.gnome.org/NetworkManager/0.9/spec.html#org.freedesktop.NetworkManager.Device.Disconnect
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/2
							- eth1
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/3
							- usb0
		"""
		
		reply = QDBusPendingReply(reply)
		if reply.isError():
			raise DBusException("%s: %s" % (reply.error().name(), reply.error().message()))
		reply = reply.value()
		
		self._networkInterfaces = [{
			'Device': QDBusInterface( #Provides node.
				f"org.freedesktop.NetworkManager", #Service
				devicePath, #Path
				f"org.freedesktop.NetworkManager.Device", #Interface
				QDBusConnection.systemBus(),
			),
			'Device.Wired': QDBusInterface( #Provides node.
				f"org.freedesktop.NetworkManager", #Service
				devicePath, #Path
				f"org.freedesktop.NetworkManager.Device.Wired", #Interface
				QDBusConnection.systemBus(),
			),
			'Device property interface': QDBusInterface( #Provides interface to get properties of previous node, because `.property()` is broken.
				"org.freedesktop.NetworkManager", #Service
				devicePath, #Path
				"org.freedesktop.DBus.Properties",#Interface
				QDBusConnection.systemBus()
			),
		} for devicePath in reply ]
		
		for interfaces in self._networkInterfaces:
			for networkInterface in interfaces.values():
				networkInterface.setTimeout(1000)
				if not networkInterface.isValid():
					log.critical(f"Error: Can not connect to NetworkManager at {networkInterface.service()}. ({networkInterface.lastError().name()}: {networkInterface.lastError().message()}) Try running `apt install network-manager`?")
					raise Exception("D-Bus Setup Error")
			
			#Deadlock fix as above.
			QDBusConnection.systemBus().registerObject(
				interfaces['Device'].path(), self )
			
			#Use above interface to look up the IP address interfaces.
			interfaces['Ip4Config'] = QDBusInterface( #Provides interface to get properties of previous node, because `.property()` is broken.
				"org.freedesktop.NetworkManager", #Service
				QDBusReply(interfaces['Device property interface'].call('Get', #Method
					'org.freedesktop.NetworkManager.Device', 'Ip4Config' )).value(), #Interface, Property → Path
				"org.freedesktop.NetworkManager.IP4Config", #Interface
				QDBusConnection.systemBus()
			)
			interfaces['Ip4Config property interface'] = QDBusInterface( #Provides interface to get properties of previous node, because `.property()` is broken.
				"org.freedesktop.NetworkManager", #Service
				interfaces['Ip4Config'].path(), #Path
				"org.freedesktop.DBus.Properties",#Interface
				QDBusConnection.systemBus()
			)
			
			interfaces['Ip6Config'] = QDBusInterface( #Provides interface to get properties of previous node, because `.property()` is broken.
				"org.freedesktop.NetworkManager", #Service
				QDBusReply(interfaces['Device property interface'].call('Get', #Method
					'org.freedesktop.NetworkManager.Device', 'Ip6Config' )).value(), #Interface, Property → Path
				"org.freedesktop.NetworkManager.IP6Config", #Interface
				QDBusConnection.systemBus()
			)
			interfaces['Ip6Config property interface'] = QDBusInterface( #Provides interface to get properties of previous node, because `.property()` is broken.
				"org.freedesktop.NetworkManager", #Service
				interfaces['Ip6Config'].path(), #Path
				"org.freedesktop.DBus.Properties",#Interface
				QDBusConnection.systemBus()
			)
			
			#Subscribe to network update signals, for ip address and carrier status.
			QDBusConnection.systemBus().connect(
				f"org.freedesktop.NetworkManager", #Service
				interfaces['Device'].path(),
				f"org.freedesktop.NetworkManager.Device", #Interface
				'PropertiesChanged', #Signal
				self.__interfacePropertiesChangedEvent,
			)
			QDBusConnection.systemBus().connect(
				f"org.freedesktop.NetworkManager", #Service
				interfaces['Device'].path(),
				f"org.freedesktop.NetworkManager.Device.Wired", #Interface
				'PropertiesChanged', #Signal
				self.__interfacePropertiesChangedEvent,
			)
			QDBusConnection.systemBus().connect( #untested, don't know how to change ip4 address
				f"org.freedesktop.NetworkManager", #Service
				QDBusReply(interfaces['Device property interface'].call('Get',
					'org.freedesktop.NetworkManager.Device', 'Dhcp4Config' ) ).value(), #Interface, Property → Path
				f"org.freedesktop.NetworkManager.Dhcp4Config", #Interface
				'PropertiesChanged', #Signal
				self.__interfacePropertiesChangedEvent,
			)
			QDBusConnection.systemBus().connect( #untested, don't know how to change ip6 address
				f"org.freedesktop.NetworkManager", #Service
				QDBusReply(interfaces['Device property interface'].call('Get',
					'org.freedesktop.NetworkManager.Device', 'Dhcp6Config' ) ).value(), #Interface, Property → Path
				f"org.freedesktop.NetworkManager.Dhcp6Config", #Interface
				'PropertiesChanged', #Signal
				self.__interfacePropertiesChangedEvent,
			)
			
		self.__rescan()
	
	def __getitem__(self, i):
		return self._connections[i]
	
	def __repr__(self):
		#pdb uses repr instad of str (which imo is more appropriate for an interactive debugging session)
		return f'{type(self)} ({self._connections})'
		
	
	def observe(self, callback):
		"""Add a function to get called when a volume is mounted or unmounted.
			
			The added function is immediately invoked."""
		
		assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
		self._callbacks += [callback]
		callback(self._connections)
	
	def unobserve(self, callback):
		"""Stop a function from getting called when a volume is mounted or unmounted."""
		
		assert callable(callback), f"Callback is not callable. (Expected function, got {callback}.)"
		self._callbacks = list(filter(
			lambda existingCallback: existingCallback != callback, 
			self._callbacks ))
	
	
	
	@pyqtSlot('QDBusMessage')
	def __interfacePropertiesChangedEvent(self, msg):
		log.info(f'Rescanning, network change detected. ({msg.arguments()})')
		self.__rescan()
	
	def __rescan(self):
		self._connections.clear()
		for interfaces in self._networkInterfaces:
			carrier = QDBusReply(
				interfaces['Device property interface'].call('Get',
					'org.freedesktop.NetworkManager.Device.Wired', 'Carrier' ) ) #Interface, Property
			if carrier.isValid() and carrier.value():
				try:
					addr = IPv4Address(
						QDBusReply(
							interfaces['Device property interface'].call(
								'Get', #Method
								'org.freedesktop.NetworkManager.Device', #Interface
								'Ip4Address', #Property
							)
						).value()
					)
					addr = IPv4Address('.'.join(reversed(str(addr).split('.')))) #So close. Truly, if there's two ways of representing information… (note: This is actually Python's fault here, the number parses fine in a browser address bar.)
				except AddressValueError:
					try:
						#"Array of tuples of IPv4 address/prefix/gateway. All 3 elements of each tuple are in network byte order. Essentially: [(addr, prefix, gateway), (addr, prefix, gateway), ...]"
						#	-- https://developer.gnome.org/NetworkManager/0.9/spec.html
						addr = IPv6Address(bytes(
							QDBusReply(
								interfaces['Ip6Config property interface'].call(
									'Get', #Method
									'org.freedesktop.NetworkManager.IP6Config', #Interface
									'Addresses', #Property
								)
							).value()[-1][0]
						))
					except (AddressValueError, IndexError):
						addr = None
				
				interface = QDBusReply(
					interfaces['Device property interface'].call(
						'Get', #Method
						'org.freedesktop.NetworkManager.Device', #Interface
						'Interface', #Property
					)
				).value()
				
				if addr:
					self._connections.append({
						'path': interfaces['Device'].path(),
						'name': defaultdict(
							lambda: 'generic connection', 
							{'e': 'ethernet', 'u': 'usb'}
						)[interface[0]],
						'address': addr,
					})
		
		log.info(f'conns: {self._connections}')
		
		for callback in self._callbacks:
			callback(self._connections)

networkInterfaces = NetworkInterfaces()
del NetworkInterfaces



#Perform self-test if launched as a standalone.
if __name__ == '__main__':
	from PyQt5.QtCore import QCoreApplication
	import signal as sysSignal
	
	app = QCoreApplication(sys.argv)
	
	#Quit on ctrl-c.
	sysSignal.sysSignal(sysSignal.SIGINT, sysSignal.SIG_DFL)
	
	print("Self-test: Retrieve exposure period.")
	print(f"Exposure is {get('exposurePeriod')}ns.")
	print("Control API self-test passed. Goodbye!")
	
	sys.exit(0)