# -*- coding: future_fstrings -*-

from random import shuffle, randint

from PyQt5 import uic, QtWidgets, QtCore

from debugger import *; dbg

import api2 as api
import settings


letters = list('123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ!@#$%&')
def randomCharacters(count: int):
	"""Return a random string without lookalike characters, 1/l, 0/O, etc."""
	
	#No random.choices yet.
	#return ''.join(choices(
	#	letters,
	#	k=count ))
	
	#OK, try this:
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
		
		self.updateNetworkInterfaceInformation()
		self.uiEnableHTTP.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiEnableSSH.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiHTTPPort.valueChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiRandomiseHTTPPort.clicked.connect(lambda:
			self.uiHTTPPort.setValue(randint(49152, 65535)))
		self.uiSSHPort.valueChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiRandomiseSSHPort.clicked.connect(lambda:
			self.uiSSHPort.setValue(randint(49152, 65535)))
		
		#api.observe('networkInterfaces', self.updateNetworkInterfaces)
		self.uiNetworkInterface.currentIndexChanged.connect(self.showNetworkInterface)
		
		self.uiDone.clicked.connect(window.back)
		
		"""
			d g n interfaces
			- gsn HTTP Access (None, Local, WWW)
			- gsn SSH  Access (None, Local, WWW)
			- gsn HTTP Port
			- gsn SSH  Port
			d g n lan IPv4 or v6 address - 192.168.1.79 (not .65?) or fe80::76e1:82ff:fe40:336e%%enp0s25
			d g n www IPv4 or v6 address - 2001:569:7140:f500:11cf:9603:70a7:8af4
			- gsn Web App password
			- gsn SSH password
			- - = not found, d = dbus, s = shell script, gsn = get/set/notify required
			
			docs: https://developer.gnome.org/NetworkManager/0.9/spec.html
			org.freedesktop.NetworkManager.Device.Wired has ipv4/6 properties
			gdbus introspect --system --dest org.freedesktop.NetworkManager.Device.Wired --object-path /org/freedesktop/NetworkManager/Device/Wired
			
			- Get network interfaces:
				> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager
					- Has ActivateConnection method in org.freedesktop.NetworkManager
					- Has GetDevices method in org.freedesktop.NetworkManager
						> gdbus call --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager --method org.freedesktop.NetworkManager.GetDevices
							- ([objectpath '/org/freedesktop/NetworkManager/Devices/0', '/org/freedesktop/NetworkManager/Devices/1', '/org/freedesktop/NetworkManager/Devices/2', '/org/freedesktop/NetworkManager/Devices/3'],)
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/0
							- This is apparently a network connection - in this case, loopback.
							- Links to IPv4/6 config.
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/1
							- eth0
							- is plugged in?
								- org.freedesktop.NetworkManager.Device.Wired property Carrier
								- [implements g interfaces] Filter org.freedesktop.NetworkManager.GetDevices to get the list of plugged-in interfaces.
							> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/DHCP4Config/0
								- yields org.freedesktop.NetworkManager.DHCP4Config
								- from ip_address' Dhcp4Config property
								- [implements g n lan IPv4 or v6] in properties & PropertiesChanged signal.
							> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/IP6Config/2
								- yields org.freedesktop.NetworkManager.IP6Config
								- from ip_address' Ip6Config property
								- [implements g n g n www IPv4 or v6] in Addresses (first item) & PropertiesChanged signal.
							- has Disconnect method
								- https://developer.gnome.org/NetworkManager/0.9/spec.html#org.freedesktop.NetworkManager.Device.Disconnect
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/2
							- eth1
						> gdbus introspect --system --dest org.freedesktop.NetworkManager --object-path /org/freedesktop/NetworkManager/Devices/3
							- usb0
		"""
	
	
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
		#api.set({'networkPassword': newPassword})
		self.showPassword(True) #So you can see it to type it in.
		self.checkPasswordExists() #Show controls. The editingFinished signal doesn't fire if we just change the contents like this, and textChanged fires too often (on every keystroke).
	
	
	def updateNetworkInterfaceInformation(self, *_):
		self.showNetworkInterface(self.uiNetworkInterface.currentIndex())
	
	
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
		interface = self.uiNetworkInterface.itemData(index)
		if interface:
			HTTPPort = f'\n :{self.uiHTTPPort.text()}' if not self.uiHTTPPort.text() == '80' else '' #don't show default ports, they're implicit
			SSHPort = f'\n -p {self.uiSSHPort.text()}' if not self.uiSSHPort.text() == '22' else ''
			
			self.uiAppUrl.setText(
				f"https://{interface['IP']}{HTTPPort}" 
				if self.uiEnableHTTP.isChecked() else
				'disabled' )
			
			self.uiSSHCommand.setText(
				f"ssh root@{interface['IP']}{SSHPort}" 
				if self.uiEnableSSH.isChecked() else
				'disabled' )
			
			#Use QREncode to display the URLs here.
			
		else:
			self.uiAppUrl.setText('disabled')
			self.uiSSHCommand.setText('disabled')
		