# -*- coding: future_fstrings -*-

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QSize, Qt


class Comment(QLabel):
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		if not showHitRects:
			self.hide()
			return
		
		self.setStyleSheet(f"""
			font-family: URW Chancery L; /*Karumbi was a nice font for this, but had really huge line-spacing. Not what we need here. Also, this font is not on the camera, but it doesn't matter because it'll never be displayed there.*/
			font-size: 14px;
			color: rgba(15,83,15,200); /*Slightly transparent dark green looks nice. 🙂*/
		""" + self.styleSheet())
		
		# Set some default text, so we can see the widget.
		if not self.text():
			self.setText('~comment~')
		
		self.setWordWrap(True)
		self.setAlignment(Qt.AlignTop | Qt.AlignLeft)


	def sizeHint(self):
		return QSize(241, 51)