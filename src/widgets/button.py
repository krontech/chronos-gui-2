from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class Button(QPushButton):

	def __init__(self, parent=None):
		super(Button, self).__init__(parent)
		
		self.setStyleSheet("""
			margin: 20px; /* Use margin to increase clickable area. Makes the whole thing much less fiddly. */
			font-size: 16px;
			background: white;
			border-left-color: rgb(50,50,50);
			border-top-color: rgb(50,50,50); /* Add a subtle 3d-ness until we figure out drop-shadows. */
			border: 1px solid black;
		""" + self.styleSheet())
		
	def sizeHint(self):
		return QSize(181, 81)