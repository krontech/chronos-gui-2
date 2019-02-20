# -*- coding: future_fstrings -*-

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
	
	Any comment or call in this file should be considered a proposal. It can all be
	changed if need be.
"""
import sys

from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtDBus import QDBusConnection

from debugger import *; dbg

# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)


class Reply(dict):
	def __init__(self, *args):
		self['value'] = args[0]


class State():
	cameraModel = "Mock Camera 1.4"


state = State() #Must be instantiated for QDBusMarshaller. 🙂


class ControlAPIMock(QObject):
	"""Function calls of the camera control D-Bus API."""
	@pyqtSlot('QVariantList', result='QVariantMap')
	def get(self, keys): #Dict[str, Any]
		return Reply({'cameraModel':'test'})
	
	@pyqtSlot(result="QVariantMap")
	def available_keys(self):
		return Reply(['cameraModel'])


if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control_mock'):
	sys.stderr.write(f"Could not register control service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	raise Exception("D-Bus Setup Error")

controlAPI = ControlAPIMock() #This absolutely, positively can't be inlined or it throws error "No such object path ...". Possibly, this is because a live reference must be kept so GC doesn't eat it?
QDBusConnection.systemBus().registerObject('/com/krontech/chronos/control_mock', controlAPI, QDBusConnection.ExportAllSlots)