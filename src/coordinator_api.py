# -*- coding: future_fstrings -*-

"""control api implementation

	See control_api_mock.py for a dummy interface to develop against.
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


class ControlAPI(QObject):
	@pyqtSlot(result="QVariantList")       #Should be QVariantMap, otherwise 😒
	def available_keys(self):
		return Reply(['nn test nn'])       #this segfaults, and
		# return {'value': ['nn test nn']} #this doesn't segfault.
	

if not QDBusConnection.systemBus().registerService('com.krontech.chronos.control'):
	sys.stderr.write(f"Could not register control service: {QDBusConnection.systemBus().lastError().message() or '(no message)'}\n")
	raise Exception("D-Bus Setup Error")

controlAPI = ControlAPI() #This absolutely, positively can't be inlined or it throws error "No such object path ...". Possibly, this is because a live reference must be kept so GC doesn't eat it?
QDBusConnection.systemBus().registerObject('/com/krontech/chronos/control', controlAPI, QDBusConnection.ExportAllSlots)