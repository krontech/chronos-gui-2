from PyQt5 import QtWidgets


class CamDoubleSpinBox(QtWidgets.QSpinBox):
	def __init__(self, _):
		super(CamDoubleSpinBox, self).__init__()
	
	def setDecimals(self, decimals):
		print(f'todo: set decimals to {decimals}')