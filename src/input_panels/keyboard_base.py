# -*- coding: future_fstrings -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtCore import pyqtSignal

from debugger import *; dbg

padding = 10


class KeyboardBase(QtWidgets.QWidget):
	"""The common class all keyboards share.
		
		There is a lot of code in common between alphanumeric
		and numeric inputs, basically, and it lives here."""
	
	onShow = pyqtSignal('QVariantMap')
	onHide = pyqtSignal()
	
	def __init__(self, window):
		super().__init__()
		
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.opener = None
		
		self.refocusFocusRingTimer = QtCore.QTimer()
		self.refocusFocusRingTimer.timeout.connect(lambda: 
			self.window().focusRing.refocus() )
		self.refocusFocusRingTimer.setSingleShot(True)
		
		self.onShow.connect(self.__handleShown)
		self.onHide.connect(self.__handleHide)
	
	
	def __handleFocusChange(self, old, new):
		focusedOnInputOrKeyboard = new == self.opener or True in [new in child.children() for child in self.children()]
		log.debug(f"Focus change: {self.objectName()}: focused is {focusedOnInputOrKeyboard}, on {new and new.objectName() or 'None'}.")
		if not focusedOnInputOrKeyboard:
			self.opener.doneEditing.emit()
	
	
	def __handleShown(self, options):
		#eg, {'focus': False, 'hints': [], 'opener': <line_edit.LineEdit object at 0x46155cb0>}
		self.show()
		self.opener = options["opener"]
		log.debug(f'set opener {self.opener.objectName()}')
		
		#Set button focus policy.
		for pane in self.children():
			for widget in pane.children():
				if type(widget) is QHBoxLayout:
					for widget in widget.children():
						widget.setFocusPolicy(
							QtCore.Qt.StrongFocus 
							if options["focus"] 
							else QtCore.Qt.NoFocus
						)
				else:
					widget.setFocusPolicy(
						QtCore.Qt.StrongFocus 
						if options["focus"] 
						else QtCore.Qt.NoFocus
					)
		
		if options["focus"]:
			self.uiClose.setFocus()
			self.window().focusRing.focusOut(immediate=True)
		else:
			self.window().focusRing.refocus()
		
		self.parent().app.focusChanged.connect(self.__handleFocusChange)
	
	def __handleHide(self):
		"""Implement the hide command communicated to us.
			
			Note: May be called several times if multiple conditions would close.
			"""
		
		log.debug(f"Hide event recieved by {self.objectName()}. (ignoring: {self.isHidden()})")
		
		#Debounce.
		if self.isHidden():
			return
		
		self.hide()
		
		contentsGeometry = self.parentWidget().screenContents.geometry()
		contentsGeometry.moveTop(0), contentsGeometry.moveLeft(0)
		self.parentWidget().screenContents.setGeometry(contentsGeometry)
		
		try:
			self.parent().app.focusChanged.disconnect(self.__handleFocusChange)
		except TypeError:
			log.warn('__handleFocusChange for alphanumeric keyboard not connected.')
		
		#Refresh focus ring position or focus on the thing that opened us, since the previously focussed button just disappeared.
		self.opener.setFocus()
		self.refocusFocusRingTimer.start(16) #Position of opener changes asynchronously.
		
		#setFocus may not fire, so let whatever opened us know we're done with it.
		self.opener.doneEditing.emit()
	