from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot


def silenceCallbacks(qtType, *elements):
	"""Silence events for the duration of a callback. Mostly skipped for this reproduction."""
	
	return pyqtSlot(qtType)(lambda callback: lambda self, *args, **kwargs: callback(self, *args, **kwargs))

@silenceCallbacks(int)
def callbackA(px: int):
	#correctly called
	print('got A', px)

@silenceCallbacks(int)
def callbackB(px: int):
	#correctly not called
	print('got B', px)


class RecordingSettings(QtWidgets.QDialog):
	@silenceCallbacks(int)
	def callbackC(self, px: int):
		#incorrectly not called
		print('got C', px)

	@silenceCallbacks(int)
	def callbackD(self, px: int):
		#incorrectly called
		print('got D', px)


	def __init__(self, window):
		super().__init__()

		spin = QtWidgets.QSpinBox()

		spin.valueChanged.connect(callbackA)
		spin.valueChanged.connect(self.callbackC)
		
		print(dir(self))
		print(self.callbackC.__repr__())
		print(self.callbackD.__repr__())
		self.callbackC(5)
		self.callbackD(6)
		print(dir(spin.valueChanged))
		print(pyqtSlot)

		layout = QtWidgets.QVBoxLayout()
		layout.addWidget(spin)
		self.setLayout(layout)
		self.show()



app = QtWidgets.QApplication([])
recSettingsWindow = RecordingSettings(app)
recSettingsWindow.show()
app.exec_()