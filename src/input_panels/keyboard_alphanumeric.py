from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from debugger import *; dbg

padding = 10


class KeyboardAlphanumeric(QtWidgets.QWidget):
	onShow = pyqtSignal('QVariantMap')
	onHide = pyqtSignal()
	
	def __init__(self, window):
		super().__init__()
		
		uic.loadUi("src/input_panels/keyboard_alphanumeric.ui", self)
		
		# Panel init.
		self.move(800-self.width(), 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.onShow.connect(self.__handleShown)
		self.onHide.connect(self.__handleHide)
		
		self.opener = None
		
		#We bounce the "done editing" idea through whatever opened us, so if whatever opened us is invalid it has the option of not closing us if it wants to. Is… is this spaghetti logic? I'm so sorry.
		self.uiClose.clicked.connect(lambda: 
			self.opener and self.opener.doneEditing.emit() )
	
	def __handleShown(self, options):
		#eg, {'focus': False, 'hints': [], 'opener': <line_edit.LineEdit object at 0x46155cb0>}
		self.show()
		self.opener = options["opener"]
		
		#Calculate keyboard height and position.
		
		#If there are no hints, hide the suggestion bar. Calculate the heigh of the panel, 
		if not options["hints"]:
			self.uiSuggestionBar.hide()
			inputGeometry = QtCore.QRect(0,padding, self.uiKeyPanel.width(), self.uiKeyPanel.height())
			self.uiKeyPanel.setGeometry(inputGeometry)
			inputGeometry.setHeight(inputGeometry.height() + padding) #This is like the opposite of a good API. It is minimally expressive.
			self.setGeometry(inputGeometry)
		else:
			self.uiSuggestionBar.show()
			inputGeometry = QtCore.QRect(0,self.uiSuggestionBar.height(), self.uiKeyPanel.width(), self.uiKeyPanel.height())
			self.uiKeyPanel.setGeometry(inputGeometry)
			inputGeometry.setHeight(inputGeometry.height() + self.uiSuggestionBar.height() + padding)
			self.setGeometry(inputGeometry)
		
		self.setGeometry(0, self.parentWidget().height() - self.height(), self.width(), self.height())
		
		
		#Calculate content position.
		
		openerGeometry = options["opener"].geometry() #Three syntaxes for "give me the member data".
		contentsGeometry = self.parentWidget().screenContents.geometry()
		screenGeometry = self.parentWidget().geometry()
		
		availableArea = QtCore.QRect(0,0, 
			screenGeometry.width(), screenGeometry.height() - inputGeometry.height() )
		
		targetVerticalLocationForInput = availableArea.height()//2 - openerGeometry.height()//2 #Calculate ideal top of *widget*, since we can't set widget center.
		idealContentsDeltaToCenter = targetVerticalLocationForInput - openerGeometry.top()
		
		#Clamp the screen delta so it never leaves part of the screen undrawn.
		if contentsGeometry.top() + idealContentsDeltaToCenter >= screenGeometry.top():
			contentsDeltaToCenter = screenGeometry.top() #We're already as low as we can go. Go no lower.
		elif contentsGeometry.bottom() + idealContentsDeltaToCenter <= availableArea.bottom():
			contentsDeltaToCenter = availableArea.height() - screenGeometry.height() + padding #Go as high as we can go, less padding so the fade still works. ;)
		else:
			contentsDeltaToCenter = idealContentsDeltaToCenter
		contentsGeometry.moveTop(
			0+contentsDeltaToCenter)
		self.parentWidget().screenContents.setGeometry(contentsGeometry)
		
		###
		###
		### TODO: make button focus policy correct, 
		### also tweak first/last button for focus wrapping.
		### See how animation looks.
		###
		###
		
		self.parent().app.focusChanged.connect(self.__handleFocusChange)
	
	def __handleHide(self):
		"""Implement the hide command communicated to us.
			
			Note: May be called several times if multiple conditions would close.
			"""
		
		#Debounce.
		if self.isHidden():
			return
		
		self.hide()
		
		contentsGeometry = self.parentWidget().screenContents.geometry()
		contentsGeometry.moveTop(0)
		self.parentWidget().screenContents.setGeometry(contentsGeometry)
		
		try:
			self.parent().app.focusChanged.disconnect(self.__handleFocusChange)
		except TypeError:
			print('Warning: __handleFocusChange for alphanumeric keyboard not connected.')
			pass
			
	
	def __handleFocusChange(self, old, new):
		focussedOnInputOrKeyboard = new == self.opener or True in [new in child.children() for child in self.children()]
		if not focussedOnInputOrKeyboard:
			self.opener.doneEditing.emit()