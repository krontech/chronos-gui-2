from PyQt5 import uic, QtWidgets, QtCore

from debugger import dbg, brk
#import api


class RecordingSettings(QtWidgets.QDialog):
	def __init__(self, window):
		super(RecordingSettings, self).__init__()
		uic.loadUi('assets/layouts/recsettingswindow.ui', self) #Maybe load f"assets/layouts/{self.__module__}.ui" in the future? Right now, it is clearer to load the files as named by the original camApp because we will need to reference them in both places.
		
		# Panel init.
		self.move(0, 0)
		self.setWindowOpacity(0.5)
		self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.cmdOK.clicked.connect(lambda: window.show('main'))
		self.cmdCancel.clicked.connect(lambda: window.show('main'))
		self.cmdDelaySettings.clicked.connect(lambda: window.show('trigger delay'))
		self.cmdRecMode.clicked.connect(lambda: window.show('recording mode'))