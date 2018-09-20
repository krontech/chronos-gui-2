"""Little wrapper class for QSettings which implements subscriptions.

Observe a key with a callback, called when the key is changed or initialized.
"""

from collections import defaultdict
from typing import Callable, Optional

from PyQt5.QtCore import QSettings

_settings = QSettings('Krontech', 'back-of-camera interface')
_callbacks = defaultdict(list)


def observe(key: str, callback: Callable[[Optional[str]], None]) -> None:
	"""Watch key for changes, calling callback when set. As with api.observe,
	this is called once when registered, to account for the transition
	from "unknown" to whatever the value is. (This is really convenient
	when writing state plumbing, so we don't have to have separate init
	and update callbacks.)
	
	Callback are invoked with the new value, before it is set.
	Callbacks are invoked in the order they are registered.
	Callbacks must accept zero or one arguments.
	
	Example:
		settings.observe('debugControlsEnabled', lambda debugControlsEnabled=False:
			print('debug on' if debugControlsEnabled) else 'debug off') )
	"""
	
	if _settings.contains(key):
		callback(_settings.value(key))
	else:
		callback()
	
	_callbacks[key].append(callback)


def setValue(key: str, value: str) -> str:
	"""See http://doc.qt.io/qt-5/qsettings.html#setValue"""
	
	#Do some typechecking, this gets confusing because the value is cast to a string (according to non-python rules) only after the app is restarted.
	if not isinstance(key, str):
		raise TypeError(f'settings.setValue(key, value) only accepts str keys, because that\'s what the underlying store accepts. It got passed the key {key}, a {type(key)}.')
	if not isinstance(value, str):
		raise TypeError(f'settings.setValue(key, value) only accepts str values, because that\'s what the underlying store accepts. It got passed the value {value}, a {type(value)}.')
	
	for callback in _callbacks[key]:
		callback(value)
	
	_settings.setValue(key, value)


def value(key: str, default: str = None) -> None:
	"""See http://doc.qt.io/qt-5/qsettings.html#value"""
	return _settings.value(key, default)