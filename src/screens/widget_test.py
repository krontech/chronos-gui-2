from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot
from PyQt5.QtSvg import QSvgWidget

from debugger import *; dbg
# import api as api


class WidgetTest(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/widget_test.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDebug.clicked.connect(lambda: self and dbg()) #"self" is needed here, won't be available otherwise.
		self.uiBack.clicked.connect(window.back)
		
		#QSvgWidget('assets/images/rotating-triangle.svg')
		self.animWidget = QSvgWidget('assets/images/rotating-triangle.svg', self)
		self.animWidget.move(200,300)
		self.anim = self.animWidget.children()[0]
		self.animTimer = self.anim.children()[0]
