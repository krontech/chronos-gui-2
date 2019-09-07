"""Provides signalTap, a generic class to transform a pyqtSignal.
	
	Usage example: Intercept a spinbox's valueChanged signal.
		```python
			def __init__(self):
				valueChangedTap = signalTap(lambda val:
					(val * self.unitValue[self.siUnit],) )
				self.valueChanged.connect(valueChangedTap.emit)
				self.valueChanged = valueChangedTap
		```
	"""

class signalTap():
	"""Generic class to transform a pyqtSignal."""
	
	def __init__(self, transformer):
		"""Create a new signal with a transformer function to be 
			called on the real signal value before propagation."""
		self.callbacks = []
		self.transformer = transformer
	
	def connect(self, fn):
		"""Invoke the function `fn` when the signal is emitted."""
		self.callbacks.append(fn)
		
	def disconnect(self, fn):
		"""Do not call `fn` when the signal is emitted any more."""
		self.callbacks.remove(fn)
	
	def emit(self, *args):
		"""Emit the transformed signal, based on the
			untransformed input values. (Invokes transformer.)"""
		for callback in self.callbacks:
			callback(*self.transformer(*args))
	
	def emitVerbatim(self, *args):
		"""Emit the transformed signal, based on the
			pre-transformed input values. (Ignores transformer.)"""
		for callback in self.callbacks:
			callback(*args)