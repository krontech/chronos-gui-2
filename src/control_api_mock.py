# -*- coding: future_fstrings -*-

"""D-Bus mock for api_mock.py to connect to."""


import random
from typing import *

from PyQt5.QtCore import pyqtSlot, QObject, QTimer, Qt
from PyQt5.QtDBus import QDBusConnection, QDBusMessage

from debugger import *; dbg


class State():
	@property
	def batteryCharge(self):
		return random.choice((1., .99, .98, .97, .96))

state = State() #Must be instantiated for QDBusMarshaller. 🙂


class ControlAPIMock(QObject):
	"""Function calls of the camera control D-Bus API."""
	
	def __init__(self):
		super().__init__()
		
		# Inject some fake update events.
		def test1():
			self.emitControlSignal('batteryCharge')
			
		self._timer1 = QTimer()
		self._timer1.timeout.connect(test1)
		self._timer1.setSingleShot(True)
		self._timer1.start(1000) #ms

	
	def emitControlSignal(self, name: str, value=None) -> None:
		"""Emit an update signal, usually for indicating a value has changed."""
		signal = QDBusMessage.createSignal('/com/krontech/chronos/control/mock', 'com.krontech.chronos.control.mock', name)
		signal << getattr(state, name) if value is None else value
		QDBusConnection.systemBus().send(signal)
	
	
	@pyqtSlot('QVariantList', result='QVariantMap')
	def get(self, keys: List[str]) -> Union[Dict[str, Any], str]:
		retval = {}
		
		for key in keys:
			if key[0] is '_' or not hasattr(state, key): # Don't allow querying of private variables.
				#QDBusMessage.createErrorReply does not exist in PyQt5, and QDBusMessage.errorReply can't be sent. As far as I can tell, we simply can not emit D-Bus errors.
				#Can't reply with a single string, either, since QVariantMap MUST be key:value pairs and we don't seem to have unions or anything.
				#The type overloading, as detailed at http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator, simply does not work in this case. The last pyqtSlot will override the first pyqtSlot with its return type.
				return {'ERROR': dump(f"The value '{key}' is not a known key to set.\nValid keys are: {[i for i in dir(state) if i[0] != '_']}")}
			
			retval[key] = getattr(state, key)
		
		return retval