# -*- coding: future_fstrings -*-

import os
from PyQt5 import uic, QtWidgets, QtCore

class Replay(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi(os.path.splitext(__file__)[0] + ".ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)