# -*- coding: future_fstrings -*-
import logging; log = logging.getLogger('Chronos.gui')
from glob import iglob
import os, subprocess, sys
from fcntl import fcntl, F_GETFL, F_SETFL

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor

import chronosGui2.api as api
from chronosGui2 import delay
from chronosGui2.debugger import *; dbg

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_Scripts
else:
	from chronosGui2.generated.chronos import Ui_Scripts

class Scripts(QtWidgets.QDialog, Ui_Scripts):
	path = '/var/camera/scripts'
	
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.uiStop.hide()
		
		self.permissionDenied = QStandardItemModel(self)
		message = self.tr(f"Can not run script: Permission Denied\nTo fix, set the executable bit on the script and ⟳refresh.\nExample: chmod +x \"{self.path}/my_script.py\"").split('\n')
		for line in message:
			line = QStandardItem(line)
			line.setFlags(Qt.NoItemFlags | Qt.ItemNeverHasChildren)
			self.permissionDenied.appendRow(line)
		
		self.scripts = QStandardItemModel(self)
		self.uiScripts.setModel(self.scripts)
		self.loadScripts()
		
		
		# Button binding.
		self.uiRefresh.clicked.connect(self.loadScripts)
		self.uiRun.clicked.connect(self.runScript)
		self.uiStop.clicked.connect(self.stopScript)
		self.uiScripts.selectionModel().currentChanged.connect(self.showSelectedOutput)
		self.uiDone.clicked.connect(window.back)
		
	
	def loadScripts(self):
		self.uiOutput.setModel(None)
		
		self.scripts.clear()
		for file in iglob('/var/camera/scripts/*'):
			entry = QStandardItem(file.split('/')[-1]) #File name.
			executable = os.access(file, os.X_OK)
			entry.setData({
				'path': file,
				'executable': executable,
				'output': QStandardItemModel(self),
				'process': None,
			}, Qt.UserRole)
			entry.setData(QColor('#000' if executable else '#666'), Qt.ForegroundRole)
			self.scripts.appendRow(entry)
		
		self.uiScripts.selectionModel().setCurrentIndex(
			self.scripts.index(0,0),
			QItemSelectionModel.ClearAndSelect,
		)
		self.showSelectedOutput(self.scripts.index(0,0))
	
	
	def runScript(self):
		index = self.uiScripts.selectionModel().currentIndex()
		script = index.data(Qt.UserRole)
		if not script['executable']:
			return
		
		log.info(f"run script {script['path']}")
		self.executeAndPoll(index)
		self.updateRunButton()
	
	def stopScript(self):
		index = self.uiScripts.selectionModel().currentIndex()
		script = index.data(Qt.UserRole)
		script['process'].kill()
	
	def scriptStopped(self, index: QtCore.QModelIndex):
		script = index.data(Qt.UserRole)
		
		script['process'] = None
		self.scripts.setData(index, script, Qt.UserRole )
		self.updateRunButton()
		
		log.info(f"stop script {script['path']}")
	
	
	def showSelectedOutput(self, index: QtCore.QModelIndex):
		script = self.scripts.itemData(index)[Qt.UserRole]
		
		self.uiOutput.setModel(
			script['output'] if script['executable'] else self.permissionDenied )
		self.uiOutput.scrollToBottom()
		
		self.updateRunButton()
	
	
	def updateRunButton(self):
		script = self.uiScripts.selectionModel().currentIndex().data(Qt.UserRole)
		
		if script['process']:
			self.uiStop.show()
			self.uiRun.hide()
		else:
			self.uiRun.show()
			self.uiStop.hide()
	
	
	def executeAndPoll(self, index: QtCore.QModelIndex):
		"""Run the user script.
			
			See http://eyalarubas.com/python-subproc-nonblock.html
			for commentary and additional approaches."""
		
		script = index.data(Qt.UserRole)
		
		proc = subprocess.Popen(
			script['path'],
			stdout=subprocess.PIPE,
			stderr=sys.stdout, #Echo stderr to our logs, so they can be retrieved and watched for debugging.
			shell=True,
			cwd=self.path,
			env={ 'GUI_PID': str(os.getpid()) } #Use this for SIGSTOP and SIGCONT, NOT SIGKILL. Run service stop chronos-gui2[-dev] for that. Note that $PPID is the parent *shell* we spawn, not the gui, which is why we provide the gui variable.
		)
		
		script['process'] = proc
		self.scripts.setData(index, script, Qt.UserRole )
		
		flags = fcntl(proc.stdout, F_GETFL)
		fcntl(proc.stdout, F_SETFL, flags | os.O_NONBLOCK)
		
		currentLine = ''
		currentEntry = QStandardItem(currentLine)
		script['output'].clear()
		script['output'].appendRow(currentEntry)
		def checkProc(*, timeout):
			nonlocal currentLine, currentEntry
			
			try:
				poll = proc.poll()
				data = proc.stdout.read()
				#this read kills the process: 
				#data = os.read(proc.stdout.fileno(), 1024)
				#read() seems a bit more stable, but still not 100%. I don't have any idea why. --DDR 2019-10-29
				
				if data:
					data = data.decode('utf8')
				if data:
					lines = data.split('\n')
					
					#Load the remainder of the current line.
					currentLine += lines[0]
					currentEntry.setData(currentLine, Qt.EditRole)
					
					#If any new line(s), append them. If they are unfinished, we'll load the remainder of them next time around.
					for line in lines[1:]:
						currentLine = line
						currentEntry = QStandardItem(line)
						script['output'].appendRow(currentEntry)
					
					lines[1:2] and self.scrollOutputToBottom(script)
						
					delay(self, timeout, lambda:
						checkProc(timeout=16) )
				elif poll is None: #Subprocess hasn't exited yet.
					delay(self, timeout, lambda:
						checkProc(timeout=max(250, timeout*2)) )
				else:
					message = f'exit {proc.poll()}'
					if currentLine:
						currentEntry = QStandardItem(message)
						script['output'].appendRow(currentEntry)
					else:
						currentEntry.setData(message, Qt.EditRole)
					self.scriptStopped(index)
					self.scrollOutputToBottom(script)
			except OSError:
				message = f'process output closed' #Exit code is None, the process is still running, we just can't read from it.
				if currentLine:
					currentEntry = QStandardItem(message)
					script['output'].appendRow(currentEntry)
				else:
					currentEntry.setData(message, Qt.EditRole)
				self.scriptStopped(index)
				self.scrollOutputToBottom(script)
		delay(self, 200, lambda: #Initial delay for startup, then try every frame at most or 4x a second at least. Hopefully we get more than 4fps. 😬
			checkProc(timeout=16) )
	
	
	def scrollOutputToBottom(self, script: dict):
		if self.uiOutput.model() == script['output']:
			self.uiOutput.scrollToBottom()
