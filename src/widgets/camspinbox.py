from PyQt5 import QtWidgets


class CamSpinBox(QtWidgets.QSpinBox):
	def __init__(self, parent):
		super(CamSpinBox, self).__init__(parent)