# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
# import api


class Stamp(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		if api.apiValues.get('cameraModel')[0:2] == 'TX':
			uic.loadUi("src/screens/stamp.txpro.ui", self)
		else:
			uic.loadUi("src/screens/stamp.chronos.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiDetailedMode.hide()
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)