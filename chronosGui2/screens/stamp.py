# -*- coding: future_fstrings -*-

import os
from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

# import chronosGui2.api as api


class Stamp(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi(os.path.splitext(__file__)[0] + ".ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiDetailedMode.hide()
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)