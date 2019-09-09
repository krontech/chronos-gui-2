# -*- coding: future_fstrings -*-

from typing import Union

from PyQt5.QtCore import pyqtProperty

from debugger import *; dbg

class SIUnitsPlugin():
	"""A mixin for numeric widgets which gives them an SI unit value."""
	
	#Specify the widget property "units", on numeric inputs, to provide a list of units to choose from. It is recommended to stick to 4, since that's how many unit buttons are on the numeric keyboard.
	allUnits = ['y', 'z', 'a', 'f', 'p', 'n', 'µ', 'm', '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
	unitValue = { #Map of units to their multipliers. eg, k = kilo = ×1000. Or µs = microseconds = ×0.000001. Usually queried with unit[:1], because something like mV or ms both have the same common numerical multiplier. [0] is not used because it fails on "".
		suffix: 10**((index-8)*3) for index, suffix in enumerate(allUnits) #Position 8 is neutral, 'no unit'.
	}
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.unitList = []
		self._unit = ''
		self._artificialUnit = True
	
	
	#Units are only really used for decimal spin boxes, but they affect the logic of the spin boxes, and the spin box logic is sort of shared with everything.
	@pyqtProperty(str)
	def units(self):
		return ','.join(self.unitList)
	
	@units.setter
	def units(self, newUnitCSVList):
		self.unitList = [s.strip() for s in newUnitCSVList.split(',') if s.strip()]
		if self._artificialUnit: #Find a natural unit, if none is set.
			if self.unitsPostfix in self.unitList:
				self.unit = self.unitsPostfix
			elif self.unitList[1:2]:
				self.unit = self.unitList[1] #¯\_(ツ)_/¯ TODO: Select most compact representation. TODO: How to deal with decimal rounding? Do we need to?
			else:
				self.unit = ''
			
			self._artificialUnit = True
	
	@pyqtProperty(str)
	def unit(self):
		return self._unit
	
	@unit.setter
	def unit(self, newUnit):
		self._unit = newUnit.strip()
		self.setSuffix(self._unit)
		self._artificialUnit = False
	
	
	@property
	def unitsPostfix(self):
		"""The common postfix of all the units.
			
			eg., if units is "kV, V, mV", then the common postfix is "V"."""
		if not self.unitList:
			return ''
		
		bins = {''}
		for x in range(len(self.unitList[0])):
			postfix = bins.pop()
			for unit in self.unitList:
				bins |= {unit[-x-1:]}
			if len(bins) != 1:
				return postfix
		return bins.pop()
	
	
	@property
	def siUnit(self):
		"""The current SI unit. (see allUnits)"""
		
		si = self.unit[0:-len(self.unitsPostfix)]
		assert si in self.unitValue, f"Unrecognised SI unit, '{si}', calculated for {self.objectName} ({self}).\nCheck all postfixes are common? (Common postfix is currently '{self.unitsPostfix}').\nAll recognised SI units are:\n{self.allUnits}"
		return si
	
	
	def realValue(self, valueFunction) -> Union[float, int]:
		"""Get real value of input, taking into account the SI units. (eg., 'k' or 'µs')"""
		
		if getattr(self, 'unitList', []):
			return valueFunction() * self.unitValue[self.siUnit]
		else:
			return valueFunction() * 1
	
	def setRealValue(self, setValueFunction, val) -> None:
		"""Set the value of the spinbox, taking into account the SI units."""
		
		if getattr(self, 'unitList', []):
			return setValueFunction(val / self.unitValue[self.siUnit])
		else:
			return setValueFunction(val / 1)
	
	
	def realMinimum(self, valueFunction) -> Union[float, int]:
		"""Get real value of input, taking into account the SI units. (eg., 'k' or 'µs')"""
		
		if getattr(self, 'unitList', []):
			return valueFunction() * self.unitValue[self.siUnit]
		else:
			return valueFunction() * 1
	
	def setRealMinimum(self, setValueFunction, val) -> None:
		"""Set the value of the spinbox, taking into account the SI units."""
		
		if getattr(self, 'unitList', []):
			return setValueFunction(val / self.unitValue[self.siUnit])
		else:
			return setValueFunction(val / 1)
	
	
	def realMaximum(self, valueFunction) -> Union[float, int]:
		"""Get real value of input, taking into account the SI units. (eg., 'k' or 'µs')"""
		
		if getattr(self, 'unitList', []):
			return valueFunction() * self.unitValue[self.siUnit]
		else:
			return valueFunction() * 1
	
	def setRealMaximum(self, setValueFunction, val) -> None:
		"""Set the value of the spinbox, taking into account the SI units."""
		
		if getattr(self, 'unitList', []):
			return setValueFunction(val / self.unitValue[self.siUnit])
		else:
			return setValueFunction(val / 1)