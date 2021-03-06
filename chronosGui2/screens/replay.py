# -*- coding: future_fstrings -*-
from PyQt5 import QtWidgets, QtCore

import chronosGui2.api as api
from chronosGui2.debugger import *; dbg

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_Replay
else:
	from chronosGui2.generated.chronos import Ui_Replay

class Replay(QtWidgets.QWidget, Ui_Replay):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.uiDone.clicked.connect(window.back)
