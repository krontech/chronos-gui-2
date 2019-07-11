# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
import api2


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
		
		rtl = api2.control.callSync('getResolutionTimingLimits', api2.getSync('resolution'))
		self.uiSlider.setMaximum(rtl['exposureMax'])
		self.uiSlider.setMinimum(rtl['exposureMin'])
		
		self.uiSlider.debounce.sliderMoved.connect(self.onExposureChanged)
		api2.observe('exposurePeriod', self.updateExposureNs)
	
	
	@pyqtSlot(int, name="updateExposureNs")
	def updateExposureNs(self, newExposureNs):
		#print(f'updating slider to {newExposureNs}')
		self.uiSlider.setValue(newExposureNs)
	
	def onExposureChanged(self, newExposureNs):
		#print(f'slider moved to {newExposureNs}')
		self.uiSlider.setValue(
			api2.control('set', {
				'exposurePeriod': newExposureNs,
			})['exposurePeriod']
		)