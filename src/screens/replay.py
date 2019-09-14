# -*- coding: future_fstrings -*-

from PyQt5 import uic, QtWidgets, QtCore

from debugger import *; dbg


class Replay(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/replay2.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)