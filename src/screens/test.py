# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api2


silenceCallbacks = api2.silenceCallbacks


class Test(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/test.widget.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDebug.clicked.connect(lambda: self and dbg()) #"self" is needed here, won't be available otherwise.
		#self.uiDebug.clicked.connect(lambda: self.decimalspinbox_3.availableUnits()) #"self" is needed here, won't be available otherwise.
		self.uiBack.clicked.connect(window.back)
		
		self.uiSlider.setMaximum(api2.get('exposureMax'))
		self.uiSlider.setMinimum(api2.get('exposureMin'))
		
		self.uiSlider.valueChanged.connect(self.onExposureChanged)
		api2.observe('exposurePeriod', self.updateExposureNs, saftyCheckForSilencedWidgets=False)
	
	
	@pyqtSlot(int, name="updateExposureNs")
	def updateExposureNs(self, newExposureNs):
		self.uiSlider.blockSignals(True)
		print(f'updating slider to {newExposureNs} (blocked {self.uiSlider.signalsBlocked()})')
		self.uiSlider.setValue(newExposureNs)
		self.uiSlider.blockSignals(False)
	
	def onExposureChanged(self, newExposureNs):
		self.uiSlider.blockSignals(True)
		self.uiSlider.setValue(
			api2.control('set', dump(f'set (blocked {self.uiSlider.signalsBlocked()})', {
				'exposurePeriod': newExposureNs//2,
			}))['exposurePeriod']
		)
		self.uiSlider.blockSignals(False)