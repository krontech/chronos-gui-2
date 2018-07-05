from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg

from touch_margin_object import TouchMarginObject, MarginWidth


class Button(QPushButton, TouchMarginObject):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginObject doesn't work.
	
	def __init__(self, parent=None, inEditor=False):
		super().__init__(parent, inEditor=inEditor)
		
		if self.inEditor:
			self.setStyleSheet("""
				/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
				font-size: 16px;
				background: white;
			""" + self.styleSheet())
		else:
			self.setStyleSheet("""
				/* App style. Use margin to provide further click area outside the visual button. */
				font-size: 16px;
				background: white;
				border: 1px solid black;
				border-left-color: rgb(50,50,50);
				border-top-color: rgb(50,50,50); /* Add a subtle 3d-ness until we figure out drop-shadows. */
			""" + self.styleSheet())


	def sizeHint(self):
		return QSize(181, 81)