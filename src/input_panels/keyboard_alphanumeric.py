from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from debugger import *; dbg


class KeyboardAlphanumeric(QtWidgets.QWidget):
	onShow = pyqtSignal(list)
	onHide = pyqtSignal()
	
	def __init__(self, window):
		super().__init__()
		
		uic.loadUi("src/input_panels/keyboard_alphanumeric.ui", self)
		
		# Panel init.
		self.move(800-self.width(), 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)