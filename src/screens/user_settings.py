from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
# import api as api


class UserSettings(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/user_settings.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)