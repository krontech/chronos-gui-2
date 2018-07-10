from random import randint

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg


class Slider(QSlider):
	def __init__(self, parent=None, inEditor=False):
		super().__init__(parent)
		
		self.inEditor = inEditor
		
		self.clickMarginColorSlider = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
		self.clickMarginColorHandle = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
		self.refreshStyle()

	def sizeHint(self):
		return QSize(81, 201)
	
	
	def refreshStyle(self):
		drawDebugArea = False
		self.setStyleSheet(f"""
			Slider {{
				background-color: {self.clickMarginColorSlider if self.inEditor or drawDebugArea else "transparent"};
				/*padding: 0 0; Additional padding between top groove and top hitbox. Doesn't work due to scroll drag speed vs slider speed issue. */
			}}
			Slider::handle:vertical {{
				image: url({"../../" if self.inEditor else ""}assets/images/handle-bars-41x81+20.png); /* File name fields: width x height + vertical padding. */
				background: {self.clickMarginColorHandle if self.inEditor or drawDebugArea else "transparent"};
				/*Setting a border here messes up scrolling; scrolling goes faster than the drag does. Something in the math is off. */
				margin: -35px -200px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
				padding: -1px;
			}}
			Slider::groove:vertical {{
				/* This slider has an extra-large hitbox, so it's easy to tap. This is done by giving it an invisible margin. A small graphic, handle-bars.png, draws the visual slider for us. Note that the real area of the slider, and it's QWidget holders, must be as large as the hitbox.*/
				border: 1px solid black;
				width: 15px; /* The groove expands to the size of the slider by default. We'll give it an explicit width. */
				margin: 35px; /* Handle needs margin to compensate for this. Controls how far from the bottom and top the groove is. */
				border-radius: 7.5px; /* Half of width. More turns it off. */
			}}
		""" + self.styleSheet())