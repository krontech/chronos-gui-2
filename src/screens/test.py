from PyQt5 import uic, QtWidgets, QtCore, QtGui
# from PyQt5.QtCore import pyqtSlot
from PyQt5.QtSvg import QSvgWidget

from debugger import *; dbg
# import api as api


class Test(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/test.widget.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDebug.clicked.connect(lambda: self and dbg()) #"self" is needed here, won't be available otherwise.
		#self.uiDebug.clicked.connect(lambda: self.decimalspinbox_3.availableUnits()) #"self" is needed here, won't be available otherwise.
		self.uiBack.clicked.connect(window.back)
		
		#QSvgWidget('assets/images/rotating-triangle.svg')
		self.animWidget = QSvgWidget('assets/images/rotating-triangle.svg', self)
		self.animWidget.move(200,300)
		self.anim = self.animWidget.children()[0]
		self.animTimer = self.anim.children()[0]
		
		self.spinbox_2.setFocus()
		
		#self.uiAnimateTriangle.clicked.connect(self.animateTriangle)
	
	def animateTriangle(self):
		#self.animTimer.stop()
		print('cf', self.anim.currentFrame())
		self.anim.setCurrentFrame(0)
		print('nf', self.anim.currentFrame())
		#self.anim.repaintNeeded.emit()
		dbg()