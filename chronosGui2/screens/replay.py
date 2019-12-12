# -*- coding: future_fstrings -*-

import os
from PyQt5 import uic, QtWidgets, QtCore

# Import the generated UI form.
from chronosGui2.generated.replay import Ui_Form as Ui_Replay

class Replay(QtWidgets.QWidget, Ui_Replay):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)