from PyQt5.QtCore import *

#Importing API may fail in Qt Designer, since we may not have it set up on the designing machine.
try:
	import api_mock as api
except Exception as e:
	api = None

from debugger import dbg, brk; dbg, brk


class DirectAPILinkPlugin():
	"""Bind an input to a Control API value from QT Designer. 🔗
	
		To use in Qt Designer, put the name of an API control variable
		in linkedValueName. To enable for a widget in Python, add to
		the inheritance chain.
		
		If more logic than a straight-through link is desired, set up
		the observer and updater on the screen the widget appears on.
	"""
	
	@pyqtProperty(str)
	def linkedValueName(self):
		return self._linkedValueName if hasattr(self, '_linkedValueName') else ''
		
	@linkedValueName.setter
	def linkedValueName(self, newLinkedValueName):
		self._linkedValueName = newLinkedValueName
		if newLinkedValueName and api: #API may not load in Qt Designer if it's not been set up.
			api.observe(newLinkedValueName, self.__updateValue)
				
			self.valueChanged.connect(
				lambda val: api.set({self._linkedValueName: val}) )
		
	
	@pyqtSlot(int, str)
	def __updateValue(self, newValue):
		self.blockSignals(True)
		self.setValue(newValue)
		self.blockSignals(False)
	__updateValue._isSilencedCallback = True #The API function that would normally set _isSilencedCallback and wrap the callback in the blockSignal() calls only works on panel-level callbacks, not component-level callbacks like this one. So, we'll just be careful and quietly disable the check ourselves. 😉