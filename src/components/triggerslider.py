from PyQt5 import QtWidgets


class TriggerSlider(QtWidgets.QSlider):
	def __init__(self, parent):
		super(TriggerSlider, self).__init__(parent)