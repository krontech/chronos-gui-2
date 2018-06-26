from PyQt5 import uic, QtWidgets, QtCore

from debugger import dbg, brk; dbg, brk
#import api


class TriggerSettings(QtWidgets.QDialog):
	def __init__(self, window):
		super(TriggerSettings, self).__init__()
		uic.loadUi('src/screens/iosettingswindow.ui', self) #Maybe load f"assets/layouts/{self.__module__}.ui" in the future? Right now, it is clearer to load the files as named by the original camApp because we will need to reference them in both places.
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		
		# Button binding.
		self.cmdOK.clicked.connect(lambda: window.show('main'))
		self.cmdCancel.clicked.connect(lambda: window.show('main'))