from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
# import api_mock as api


class PrimarySettings(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/primary_settings.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)
		self.uiFileSaving.clicked.connect(lambda: window.show('file_settings'))
		self.uiUserSettings.clicked.connect(lambda: window.show('user_settings'))
		self.uiAboutCamera.clicked.connect(lambda: window.show('about_camera'))
		self.uiUpdateCamera.clicked.connect(lambda: window.show('update_firmware'))