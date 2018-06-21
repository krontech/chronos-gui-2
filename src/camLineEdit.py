from PyQt5 import QtWidgets


class CamLineEdit(QtWidgets.QLineEdit):
	def __init__(self, parent):
		super(CamLineEdit, self).__init__(parent)