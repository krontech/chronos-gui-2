from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg
# import api_mock as api


class AboutCamera(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/make-dbus-work.ui', self) #DDR 2018-07-12: QDBusConnection.systemBus().connect, in api.py, doesn't return if we don't load this here. I don't know what an empty dialog box has to do with anything. 🤷
		uic.loadUi("src/screens/about_camera.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Set scroll bar to scroll all text content. 
		self.uiScroll.setMaximum( 
			#text height * wtf - window height + margin
			self.uiText.height()*2 - self.uiScrollArea.height() + 20 )
		
		# Button binding.
		self.uiScroll.valueChanged.connect(self.scrollPane)
		
		self.uiDone.clicked.connect(window.back)
		
	def scrollPane(self, pos):
		"""Update the text position when scrollbar changes.
		
			I can't figure out how to scroll the scroll-pane itself. 😝 This just
			scrolls the text widget itside it, which seems to be horrendously
			inefficient.
		"""
		geometry = self.uiText.geometry()
		geometry.setTop(-pos)
		self.uiText.setGeometry(geometry)