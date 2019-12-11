# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore

from debugger import *; dbg


class Replay(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		if api.apiValues.get('cameraModel')[0:2] == 'TX':
			uic.loadUi("src/screens/replay2.txpro.ui", self)
		else:
			uic.loadUi("src/screens/replay2.chronos.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)