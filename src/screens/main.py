from PyQt5 import uic, QtWidgets, QtCore

from debugger import dbg, brk
import api


class Main(QtWidgets.QDialog):
	def __init__(self, window):
		super(Main, self).__init__()
		uic.loadUi('assets/layouts/cammainwindow.ui', self) #Maybe load f"assets/layouts/{self.__module__}.ui" in the future? Right now, it is clearer to load the files as named by the original camApp because we will need to reference them in both places.
		
		# Panel init.
		self.move(0, 0)
		self.setWindowOpacity(0.5)
		self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.cmdDebugWnd.clicked.connect(self.printExposureNs)
		self.cmdRecSettings.clicked.connect(lambda: window.show('recording settings'))
		self.cmdIOSettings.clicked.connect(lambda: window.show('trigger settings'))
		self.cmdUtil.clicked.connect(lambda: window.show('settings'))
	
	# @pyqtSlot() is not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details. (import with `from PyQt5.QtCore import pyqtSlot`)
	def printExposureNs(self) -> None:
		print("exposure is %ins" % api.control('get_video_settings')["exposureNsec"])