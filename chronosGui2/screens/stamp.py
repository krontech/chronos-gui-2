# -*- coding: future_fstrings -*-

import os
from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

# Import the generated UI form.
from chronosGui2.generated.chronos import Ui_Stamp

class Stamp(QtWidgets.QDialog, Ui_Stamp):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiDetailedMode.hide()
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)
