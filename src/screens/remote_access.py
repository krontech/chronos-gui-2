# -*- coding: future_fstrings -*-

from random import shuffle, randint
from hashlib import sha256
import binascii
import json
import subprocess
import re

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtGui import QPixmap

from debugger import *; dbg

import api2 as api
import settings
import external_process


webServer = QtCore.QSettings('Krontech', 'web interface')


def hexHash(*, password: str):
	return binascii.hexlify(
		sha256(
			bytes(api.apiValues.get('cameraSerial'), 'utf-8') + 
			sha256(bytes(password, 'utf-8')).digest()
		).digest()
	).decode('utf-8')


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


#from https://stackoverflow.com/questions/13179126/how-to-change-a-linux-user-password-from-python import setPassword
def execSetPassword(userName:str, password:str):
	p = subprocess.Popen(['chpasswd'], universal_newlines=True, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(stdout, stderr) = p.communicate(userName + ":" + password + "\n")
	assert p.wait() == 0
	if stdout or stderr:
		raise Exception("Error encountered changing the password!")


class RemoteAccess(QtWidgets.QWidget):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/remote_access.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Widget binding.
		self.uiDebug.clicked.connect(lambda: self and window and dbg())
		
		# Password-related stuff.
		self.checkPasswordExists()
		self.uiPassword.selectionChanged.connect(self.clearPasswordIfInitial)
		self.uiPassword.editingFinished.connect(self.checkPasswordExists)
		self.uiPassword.editingFinished.connect(self.onNewPassword)
		self.uiShowPassword.clicked.connect(lambda: self.showPassword())
		self.uiRandomisePassword.clicked.connect(self.randomisePassword)
		
		# Services
		self.updateNetworkInterfaceInformation()
		
		#Only set status on startup, because we'll set it async as we start and stop services later.
		self.uiHTTPStatus.showMessage(
			f"Status: {'Running' if settings.value('http enabled', True) else 'Stopped'}", 
			timeout = 0 )
		
		self.uiSSHStatus.showMessage(
			f"Status: {'Running' if settings.value('ssh enabled', True) else 'Stopped'}", 
			timeout = 0 )
		
		settings.observe('http enabled', True, lambda enabled: (
			self.uiEnableHTTP.setChecked(enabled) ))
		self.uiEnableHTTP.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiEnableHTTP.stateChanged.connect(lambda state: self.setHTTP(on=bool(state)))
		
		settings.observe('ssh enabled', False, lambda enabled:
			self.uiEnableSSH.setChecked(enabled) )
		self.uiEnableSSH.stateChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiEnableSSH.stateChanged.connect(lambda state: self.setSSH(on=bool(state)))
		
		settings.observe('http port', 80, lambda enabled:
			self.uiHTTPPort.setValue(enabled) )
		self.uiHTTPPort.valueChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiHTTPPort.valueChanged.connect(lambda num: self.setHTTPPort(num))
		
		self.uiRandomiseHTTPPort.clicked.connect(lambda:
			self.uiHTTPPort.setValue(randint(49152, 65535)) )
		
		settings.observe('ssh port', 22, lambda enabled:
			self.uiSSHPort.setValue(enabled) )
		self.uiSSHPort.valueChanged.connect(self.updateNetworkInterfaceInformation)
		self.uiSSHPort.valueChanged.connect(lambda num: self.setSSHPort(num))
		
		self.uiRandomiseSSHPort.clicked.connect(lambda:
			self.uiSSHPort.setValue(randint(49152, 65535)) )
		
		api.networkInterfaces.observe(self.updateNetworkInterfaces)
		self.uiNetworkInterface.currentIndexChanged.connect(self.updateNetworkInterface)
		
		# Navigation
		self.uiDone.clicked.connect(window.back)
	
	
	def checkPasswordExists(self):
		if self.uiPassword.text() == '«pass»' and webServer.value('password', '') == '':
			self.showPassword(visible=True)
		
		if self.uiPassword.text() and (self.uiPassword.text() != '«pass»' or webServer.value('password', '')):
			self.uiPasswordExplanation.hide()
			self.uiAllConfigOptions.show()
		else:
			self.uiAllConfigOptions.hide()
			self.uiPasswordExplanation.show()
			
	def onNewPassword(self):
		self.setPassword(self.uiPassword.text())
	
	
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
		
		if echoMode == QtWidgets.QLineEdit.Normal and self.uiPassword.text() == "«pass»": #This value can not be entered; it's used as a flag to mark that we haven't fiddled with the password yet.
			self.uiPassword.clear()
	
	
	def clearPasswordIfInitial(self, *_):
		if self.uiPassword.text() == "«pass»":
			self.uiPassword.clear()
			self.uiPassword.setEchoMode(QtWidgets.QLineEdit.Normal)
	
	
	def randomisePassword(self):
		newPassword = randomCharacters(8)
		self.uiPassword.setText(newPassword)
		#api.set({'networkPassword': newPassword})
		self.showPassword(True) #So you can see it to type it in.
		self.checkPasswordExists() #Show controls. The editingFinished signal doesn't fire if we just change the contents like this, and textChanged fires too often (on every keystroke).
	
	
	def updateNetworkInterfaces(self, interfaces):
		#Interfaces is like:
		#	[{'address': IPv4Address('192.168.1.101'),
		#	  'name': 'ethernet',
		#	  'path': '/org/freedesktop/NetworkManager/Devices/1'},
		#	 {'address': IPv4Address('192.168.12.1'),
		#	  'name': 'usb',
		#	  'path': '/org/freedesktop/NetworkManager/Devices/3'}]
		
		self.uiNetworkInterface.clear()
		for interface in interfaces:
			self.uiNetworkInterface.addItem(interface['name'], interface)
		
		#Do something here to set the selected item to the newest interface, whatever wasn't used last time ought to be fine?
		#if self.uiNetworkInterface.currentIndex() < 0:
		#	self.uiNetworkInterface.setCurrentIndex(0)
		
		self.updateNetworkInterfaceInformation() #Fix bug where network information was disabled as if there were no connections, if you opened the screen vs restarting the app with the screen opened.
	
	def updateNetworkInterfaceInformation(self, *_):
		self.updateNetworkInterface(self.uiNetworkInterface.currentIndex())
	
	def updateNetworkInterface(self, index):
		interface = self.uiNetworkInterface.itemData(index)
		commandWhenDisabled = '-'
		if interface:
			self.uiNoNetworkConnection.hide()
			self.uiNetworkInterfaceInformation.show()
			self.uiNetworkInterface.show()
			
			HTTPPort = f'\n :{self.uiHTTPPort.text()}' if not self.uiHTTPPort.text() == '80' else '' #don't show default ports, they're implicit
			SSHPort = f'\n -p {self.uiSSHPort.text()}' if not self.uiSSHPort.text() == '22' else ''
			appUrl = f"http://{interface['address']}{HTTPPort}" 
			sshCommand = f"ssh root@{interface['address']}{SSHPort}"
			
			self.uiAppUrl.setText(
				appUrl if self.uiEnableHTTP.isChecked() else commandWhenDisabled )
			self.uiSSHCommand.setText(
				sshCommand if self.uiEnableSSH.isChecked() else commandWhenDisabled )
			
			self.updateQRCodes()
			
		else:
			self.uiNoNetworkConnection.show()
			self.uiNetworkInterfaceInformation.hide()
			self.uiNetworkInterface.hide()
			self.uiAppUrlQRCode.hide()
			self.uiSSHCommandQRCode.hide()
			
			self.uiAppUrl.setText(commandWhenDisabled)
			self.uiSSHCommand.setText(commandWhenDisabled)
	
	
	def updateQRCodes(self):
		interface = self.uiNetworkInterface.currentData()
		HTTPPort = f'\n :{self.uiHTTPPort.text()}' if not self.uiHTTPPort.text() == '80' else '' #don't show default ports, they're implicit
		SSHPort = f'\n -p {self.uiSSHPort.text()}' if not self.uiSSHPort.text() == '22' else ''
		appUrl = f"http://{interface['address']}{HTTPPort}/app" 
		sshCommand = f"ssh root@{interface['address']}{SSHPort}"
		
		external_process.run(self,
			['qrencode', '-o', '-', appUrl],
			lambda err: None,
			lambda data: self.updateAppQRCode(self.uiAppUrlQRCode, data),
			binaryOutput = True,
		)
		external_process.run(self,
			['qrencode', '-o', '-', sshCommand],
			lambda err: None,
			lambda data: self.updateAppQRCode(self.uiSSHCommandQRCode, data),
			binaryOutput = True,
		)
	
	def updateAppQRCode(self, target, qrCodePng):
		qrCodePixmap = QPixmap()
		qrCodePixmap.loadFromData(
			qrCodePng, 'png', QtCore.Qt.MonoOnly )
		border = 10 #px
		qrCodePixmap = qrCodePixmap.copy(QtCore.QRect(
			border, border,
			qrCodePixmap.width() - border*2, qrCodePixmap.height() - border*2
		))
		target.setPixmap(qrCodePixmap)
		target.show()
		
	
	
	def setPassword(self, password):
		log.print(f'setPassword {password}')
		settings.setValue('password', password)
		self.setHTTPPassword(password)
		self.setSSHPassword(password)
	
	def setHTTPPassword(self, password): #password
		webServer.setValue('password',
			hexHash(password=password) if password else '' )
		self.reloadHTTP()

	def setSSHPassword(self, password):
		try:
			execSetPassword('root', password) #We should reeeeeally switch Web and SSH to someone else.
		except Exception as e:
			log.error(str(e))
		self.reloadSSH()


	def setSSH(self, *, on=True):
		log.print(f'setSSH {on}')
		settings.setValue('ssh enabled', on)
			
		if on:
			self.uiSSHStatus.showMessage(
				f"Status: Starting…",
				timeout = 0 )
			
			external_process.run(self,
				['systemctl', 'enable', 'ssh'],
				
				lambda err: (
					self.uiSSHStatus.showError(
						f"Status: Error. See journalctl.", 
						timeout = 0 ),
					log.error(err),
				),
				
				lambda *_: external_process.run(self,
					['service', 'ssh', 'start'],
					
					lambda err: (
						self.uiSSHStatus.showError(
							f"Status: Error. See journalctl.", 
							timeout = 0 ),
						log.error(err),
					),
					
					lambda *_:
						self.uiSSHStatus.showMessage(
							f"Status: Running.",
							timeout = 0 )
				)
			)
		
		else: #off
			self.uiSSHStatus.showMessage(
				f"Status: Stopping…",
				timeout = 0 )
			
			external_process.run(self,
				['service', 'ssh', 'stop'],
				
				lambda err: (
					self.uiSSHStatus.showError(
						f"Status: Error. See journalctl.", 
						timeout = 0 ),
					log.error(f'Internal command failed with code {err}.'),
				),
				
				lambda *_: external_process.run(self,
					['systemctl', 'disable', 'ssh'],
					
					lambda err: (
						self.uiSSHStatus.showError(
							f"Status: Error. See journalctl.", 
							timeout = 0 ),
						log.error(f'Internal command failed with code {err}.'),
					),
					
					lambda *_:
						self.uiSSHStatus.showMessage(
							f"Status: Stopped.",
							timeout = 0 )
				)
			)

	def setSSHPort(self, num):
		log.print(f'setSSHPort {num}')
		settings.setValue('ssh port', num)
		
		#lol i bet this is going to cause problems
		with open('/etc/ssh/sshd_config', 'r+', encoding='utf8') as sshd_config:
			configuration = sshd_config.read()
			sshd_config.seek(0)
			print(
				re.sub(
					r'\n#? ?Port \d+\n',
					f'\nPort {num}\n',
					configuration,
				),
				file = sshd_config, 
				end = '',
			)
			sshd_config.truncate()
		
		self.reloadSSH()
	
	def reloadSSH(self):
		if not settings.value('ssh enabled', False):
			return
		
		self.uiSSHStatus.showMessage(
			f"Status: Working…",
			timeout = 0 )
		
		external_process.run(self,
			['service', 'ssh', 'reload'],
			
			lambda err: (
				self.uiSSHStatus.showError(
					f"Status: Error. (See journalctl -xn.)", 
					timeout = 0 ),
				log.error(f'Internal command failed with code {err}.'),
			),
			
			lambda *_:
				self.uiSSHStatus.showMessage(
					f"Status: Running.",
					timeout = 0 )
		)


	def setHTTP(self, *, on=True):
		log.print(f'setHTTP {on}')
		settings.setValue('http enabled', on)
		
		if on:
			self.uiHTTPStatus.showMessage(
				f"Status: Starting…",
				timeout = 0 )
			
			external_process.run(self,
				['systemctl', 'enable', 'chronos-web-api'],
				
				lambda err: (
					self.uiHTTPStatus.showError(
						f"Status: Error. See journalctl.", 
						timeout = 0 ),
					log.error(f'Internal command failed with code {err}.'),
				),
				
				lambda *_: external_process.run(self,
					['service', 'chronos-web-api', 'start'],
					
					lambda err: (
						self.uiHTTPStatus.showError(
							f"Status: Error. See journalctl.", 
							timeout = 0 ),
						log.error(f'Internal command failed with code {err}.'),
					),
					
					lambda *_:
						self.uiHTTPStatus.showMessage(
							f"Status: Running.",
							timeout = 0 )
				)
			)
		
		else: #off
			self.uiHTTPStatus.showMessage(
				f"Status: Stopping…",
				timeout = 0 )
			
			external_process.run(self,
				['service', 'chronos-web-api', 'stop'],
				
				lambda err: (
					self.uiHTTPStatus.showError(
						f"Status: Error. See journalctl.", 
						timeout = 0 ),
					log.error(err),
				),
				
				lambda *_: external_process.run(self,
					['systemctl', 'disable', 'chronos-web-api'],
					
					lambda err: (
						self.uiHTTPStatus.showError(
							f"Status: Error. See journalctl.", 
							timeout = 0 ),
						log.error(err),
					),
					
					lambda *_:
						self.uiHTTPStatus.showMessage(
							f"Status: Stopped.",
							timeout = 0 )
				)
			)

	def setHTTPPort(self, num):
		log.print(f'setHTTPPort {num}')
		settings.setValue('http port', num)
		webServer.setValue('port', json.dumps(num))
		self.reloadHTTP()
	
	def reloadHTTP(self):
		if not settings.value('http enabled', True):
			return
		
		self.uiHTTPStatus.showMessage(
			f"Status: Working…",
			timeout = 0 )
		
		external_process.run(self,
			['service', 'chronos-web-api', 'restart'],
			
			lambda err: (
				self.uiHTTPStatus.showError(
					f"Status: Error. See journalctl.", 
					timeout = 0 ),
				log.error(err),
			),
			
			lambda *_:
				self.uiHTTPStatus.showMessage(
					f"Status: Running.",
					timeout = 0 )
		)