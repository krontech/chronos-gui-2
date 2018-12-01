"""Mock for the C-based video API.

	Usage:
	import api_mock as api
	print(api.video('thing'))
	
	Any comment or call in this file should be 
	considered a proposal, at best, or a bug.
"""

import sys
#import random
from debugger import *; dbg

from PyQt5.QtCore import pyqtSlot, QObject, QTimer, Qt, QByteArray
from PyQt5.QtDBus import QDBusConnection, QDBusMessage, QDBusError


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)



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
	#Overlay Stuff
	textbox0Content = 'textbox 0 sample text'
	textbox0Font = list(b'<binary font data here>')
	textbox0Color = 0xFFFFFF20 #RGBA
	textbox0X = 0x0008
	textbox0Y = 0x0010
	textbox0W = 0x02D0
	textbox0H = 0x0028
	textbox0Justification = 'left' #'right', or 'center'
	textbox1Content = 'textbox 1 sample text'
	textbox1Font = list(b'<binary data here>')
	textbox1Color = 0xFFFFFF20 #RGBA
	textbox1X = 0x0110
	textbox1Y = 0x03D8
	textbox1W = 0x0320
	textbox1H = 0x0028
	textbox1Justification = 'left' #'right', or 'center'
	chronosWatermarkColor = 0x20202020 #RGBA #Not implemented from here on down
	chronosWatermarkX = 0x0008
	chronosWatermarkY = 0x02F8
	rgbImage = list(b'<binary data here>')
	rgbLogoPalette = list(b'<binary LUT here>')
	rgbImageX = 0x0190
	rgbImageY = 0x0258
	rgbImageWidth = 0x0080
	rgbImageHeight = 0x0080


class VideoAPIMock(QObject):
	"""Function calls of the video control D-Bus API."""

	def emitControlSignal(self, name, value=None):
		"""Emit an update signal, usually for indicating a value has changed."""
		signal = QDBusMessage.createSignal('/com/krontech/chronos/control/mock', 'com.krontech.chronos.control.mock', name)
		signal << getattr(state, name) if value is None else value
		QDBusConnection.systemBus().send(signal)
	
	def emitError(self, message):
		error = QDBusMessage.createError(QDBusError.Other, message)
		QDBusConnection.systemBus().send(error)
		return error
	
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def status(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def flush(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def configure(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def playback(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def livedisplay(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def recordfile(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def stop(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def overlay(self, arg):
		return True
	
	@pyqtSlot('QVariantMap', result='QVariantMap')
	def livestream(self, arg):
		return True
	