# -*- coding: future_fstrings -*-

from random import shuffle, randint

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

from debugger import *; dbg

import api
from api import silenceCallbacks
import settings


def randomCharacters(count: int):
	"""Return a random string without lookalike characters, 1/l, 0/O, etc."""
	
	#No random.choices yet.
	#return ''.join(choices(
	#	'0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ!@#$%&',
	#	k=count ))
	
	#OK, try this:
	letters = list('123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ!@#$%&')
	shuffle(letters)
	return ''.join(letters[:count])
	
	#Perhaps a random phrase would be better? If we install a dictionary...
	#bash: shuf -n3 /usr/share/dict/american-english

class RemoteAccess(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/remote_access.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Widget binding.
		
		#Password-related stuff.
		self.checkPasswordExists()
		self.uiPassword.editingFinished.connect(self.checkPasswordExists)
		self.showPassword(settings.value('show network password', 'false') == 'true')
		self.uiShowPassword.clicked.connect(lambda: self.showPassword())
		self.uiRandomisePassword.clicked.connect(self.randomisePassword)
		
		self.uiEnableLocalHTTP.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiEnableRemoteHTTP.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiEnableLocalSSH.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiEnableRemoteSSH.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiHTTPPort.valueChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiRandomiseHTTPPort.clicked.connect(lambda:
			self.uiHTTPPort.setValue(randint(49152, 65535)))
		self.uiSSHPort.valueChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiRandomiseSSHPort.clicked.connect(lambda:
			self.uiSSHPort.setValue(randint(49152, 65535)))
		
		api.observe('networkInterfaces', self.updateNetworkInterfaces)
		self.uiNetworkInterface.currentIndexChanged.connect(self.showNetworkInterface)
		
		self.uiDone.clicked.connect(window.back)
	
	
	def checkPasswordExists(self):
		if self.uiPassword.text():
			self.uiPasswordExplanation.hide()
			self.uiAllConfigOptions.show()
		else:
			self.uiAllConfigOptions.hide()
			self.uiPasswordExplanation.show()
	
	
	def showPassword(self, visible=None):
		if visible == True:
			echoMode = QtWidgets.QLineEdit.Normal
		elif visible == False:
			echoMode = QtWidgets.QLineEdit.Password
		elif visible == None:
			echoMode = QtWidgets.QLineEdit.Normal if self.uiPassword.echoMode() != QtWidgets.QLineEdit.Normal else QtWidgets.QLineEdit.Password
		else:
			raise ValueError(f'Unknown visibility value "{visible}".')
		
		self.uiPassword.setEchoMode(echoMode)
		settings.setValue('show network password', 'true' if echoMode == QtWidgets.QLineEdit.Normal else "false")
	
	
	def randomisePassword(self):
		newPassword = randomCharacters(8)
		self.uiPassword.setText(newPassword)
		api.set({'networkPassword': newPassword})
		self.showPassword(True) #So you can see it to type it in.
		self.checkPasswordExists() #Show controls. The editingFinished signal doesn't fire if we just change the contents like this, and textChanged fires too often (on every keystroke).
	
	
	def updateNetworkInterfaceInformation(self):
		self.showNetworkInterface(self.uiNetworkInterface.currentIndex())
	
	
	@pyqtSlot(int, name="updateNetworkInterfaces")
	@silenceCallbacks()
	def updateNetworkInterfaces(self, interfaces):
		if interfaces:
			self.uiNoNetworkConnection.hide()
			self.uiNetworkInterfaceInformation.show()
			self.uiNetworkInterface.show()
			self.uiNetworkInterface.clear()
			for interface in interfaces:
				self.uiNetworkInterface.addItem(interface['name'], interface)
			self.showNetworkInterface(0) #Update elements in uiNetworkInterfaceInformation.
		else:
			self.uiNoNetworkConnection.show()
			self.uiNetworkInterfaceInformation.hide()
			self.uiNetworkInterface.hide()
	
	def showNetworkInterface(self, index):
		data = self.uiNetworkInterface.itemData(index)
		if not data:
			return
		
		HTTPPort = f'\n    :{self.uiHTTPPort.text()}' if not self.uiHTTPPort.text() == '80' else '' #don't show default ports, they're implicit
		SSHPort = f'\n    -p {self.uiSSHPort.text()}' if not self.uiSSHPort.text() == '22' else ''
		
		if self.uiEnableRemoteHTTP.isChecked():
			url = f"https://{data['remoteAddress4'] or data['localAddress4']}{HTTPPort}/"
		elif self.uiEnableLocalHTTP.isChecked():
			url = f"http://{data['localAddress4']}{HTTPPort}/"
		else:
			url = 'disabled'
		self.uiAppUrl.setText(url)
		
		if self.uiEnableRemoteSSH.isChecked():
			command = f"ssh root@{data['remoteAddress4'] or data['localAddress4']}{SSHPort}"
		elif self.uiEnableLocalSSH.isChecked():
			command = f"ssh root@{data['localAddress4']}{SSHPort}"
		else:
			command = 'disabled'
		self.uiSSHCommand.setText(command)