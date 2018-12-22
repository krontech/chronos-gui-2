from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from debugger import *; dbg


class KeyboardNumeric(QtWidgets.QWidget):
	onShow = pyqtSignal()
	onHide = pyqtSignal()
	
	def __init__(self, window, uiFilePath):
		super().__init__()
		uic.loadUi(uiFilePath, self)
		
		# Panel init.
		self.move(800-self.width(), 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)


class KeyboardNumericWithUnits(KeyboardNumeric):
	def __init__(self, window):
		super().__init__(window, "src/input_panels/keyboard_numeric.with_units.right-handed.ui")


class KeyboardNumericWithoutUnits(KeyboardNumeric):
	def __init__(self, window):
		super().__init__(window, "src/input_panels/keyboard_numeric.without_units.ui")