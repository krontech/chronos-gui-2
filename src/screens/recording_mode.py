from PyQt5 import uic, QtWidgets, QtCore

from debugger import dbg, brk
#import api


class RecordingMode(QtWidgets.QDialog):
	def __init__(self, window):
		super(RecordingMode, self).__init__()
		uic.loadUi('assets/layouts/recmodewindow.ui', self) #Maybe load f"assets/layouts/{self.__module__}.ui" in the future? Right now, it is clearer to load the files as named by the original camApp because we will need to reference them in both places.
		
		# Panel init.
		self.move(0, 0)
		self.setWindowOpacity(0.5)
		self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.cmdOK.clicked.connect(lambda: window.show('recording settings'))
		self.cmdCancel.clicked.connect(lambda: window.show('recording settings'))