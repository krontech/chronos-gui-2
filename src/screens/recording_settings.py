from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot


#Expected output when spinning the spinbox:
#	got A 1
#	got C 1
#However, the actual output is:
#	got A 1
#	got D 1
#This is wrong because the spinbox is hooked up to
#	callbackA
#	self.callbackC
#I do not know why D is being called, since I don't actually reference
#it anywhere. However, if we remove any of the decorators from C or D
#they work again. If we move them to the top level, out of
#RecordingSettings, they work again. What am I doing wrong?


def silenceCallbacks(*elements):
	"""Silence events for the duration of a callback. Mostly skipped for this reproduction."""
	def silenceCallbacksOf(callback):
		def silencedCallback(self, *args, **kwargs):
			callback(self, *args, **kwargs)
		return silencedCallback
	return silenceCallbacksOf


@pyqtSlot(int)
@silenceCallbacks()
def callbackA(px: int):
	print('got A', px)
	
@pyqtSlot(int) #this overwrites the last three functions
@silenceCallbacks()
def callbackB(px: int):
	print('got B', px)


class RecordingSettings(QtWidgets.QDialog):
	@pyqtSlot(int)
	@silenceCallbacks()
	def callbackC(self, px: int):
		print('got C', px)
		
	@pyqtSlot(int) #this overwrites the previous pyqtSlot-decorated function
	@silenceCallbacks()
	def callbackD(self, px: int):
		print('got D', px)
		
		
	def __init__(self, window):
		super().__init__()
		
		spin = QtWidgets.QSpinBox()
		
		spin.valueChanged.connect(callbackA)
		spin.valueChanged.connect(self.callbackC)
		
		layout = QtWidgets.QVBoxLayout()
		layout.addWidget(spin)
		self.setLayout(layout)
		self.show()



app = QtWidgets.QApplication([])
recSettingsWindow = RecordingSettings(app)
recSettingsWindow.show()
app.exec_()