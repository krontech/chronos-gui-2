from debugger import dbg, brk; dbg, brk

from PyQt5 import QtWidgets


class CamDoubleSpinBox(QtWidgets.QSpinBox):
	def __init__(self, parent):
		super(CamDoubleSpinBox, self).__init__(parent)
	
	def setDecimals(self, decimals):
		print(f'todo: set decimals to {decimals}')