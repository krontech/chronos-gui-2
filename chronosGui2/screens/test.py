# -*- coding: future_fstrings -*-
import os
from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from chronosGui2.debugger import *; dbg
import chronosGui2.api as api


class Test(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi(os.path.splitext(__file__)[0] + ".widget.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.window_ = window
		self.state = 0
		self.aShortPeriodOfTime = QtCore.QTimer()
		self.aShortPeriodOfTime.timeout.connect(self.afterAShortPeriodOftime)
		self.aShortPeriodOfTime.start(16) #One frame is a short period of time.
		
		# Button binding.
		self.uiDebug.clicked.connect(lambda: self and dbg()) #"self" is needed here, won't be available otherwise.
		#self.uiDebug.clicked.connect(lambda: self.decimalspinbox_3.availableUnits()) #"self" is needed here, won't be available otherwise.
		self.uiBack.clicked.connect(window.back)
		
		rtl = api.control.callSync('getResolutionTimingLimits', api.getSync('resolution'))
		self.uiSlider.setMaximum(rtl['exposureMax'])
		self.uiSlider.setMinimum(rtl['exposureMin'])
		
		self.uiSlider.debounce.sliderMoved.connect(self.onExposureChanged)
		api.observe('exposurePeriod', self.updateExposureNs)
		
		
	
	
	@pyqtSlot(int, name="updateExposureNs")
	def updateExposureNs(self, newExposureNs):
		#print(f'updating slider to {newExposureNs}')
		self.uiSlider.setValue(newExposureNs)
	
	def onExposureChanged(self, newExposureNs):
		#print(f'slider moved to {newExposureNs}')
		api.set('exposurePeriod', newExposureNs)
	
	def afterAShortPeriodOftime(self):
		return self.aShortPeriodOfTime.stop()
		
		self.state += 1
		if self.state == 1:
			self.decimalspinbox.setFocus()
		elif self.state == 2:
			#self.window_.app.window.showInput(self.decimalspinbox, 'alphanumeric', focus=False)
			#self.window_.app.window.showInput(self.decimalspinbox, 'numeric_without_units', focus=False)
			self.window_.app.window.showInput(self.decimalspinbox, 'numeric_with_units', focus=False)
		elif self.state == 3:
			self.aShortPeriodOfTime.stop()
		else:
			raise ValueError(f"Invalid test state {self.state}.")
		