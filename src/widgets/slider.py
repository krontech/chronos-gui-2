# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QSlider

from debugger import *; dbg
from focusable_plugin import FocusablePlugin


class Slider(QSlider, FocusablePlugin):
	"""Styled, focussable QSlider. Contains fixed valueChanged event.
		
		When overriding self.paintEvent, always make sure to call
		self.checkForVisualChange."""
	
	#Less frequent version of parent valueChanged. Only fires on visual changes.
	valueChanged = pyqtSignal(int)
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.showHitRects = showHitRects
		
		self.clickMarginColorSlider = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
		self.clickMarginColorHandle = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
		self.refreshStyle()
		
		self.jogWheelLowResolutionRotation.connect(lambda delta, pressed: 
			not pressed and self.selectWidget(delta) )
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Space))
		
		#Synthesize an update signal which does not fire much faster than repaint, as valueChanged does.
		self.__lastValue = self.value()
		self.paintEvent = self.checkForVisualChange

	def sizeHint(self):
		return QSize(81, 201)
	
	
	def refreshStyle(self):
		drawDebugArea = False
		self.setStyleSheet(f"""
			Slider {{
				background-color: {self.clickMarginColorSlider if self.showHitRects or drawDebugArea else "transparent"};
				/*padding: 0 0; Additional padding between top groove and top hitbox. Doesn't work due to scroll drag speed vs slider speed issue. */
			}}
			
			Slider::handle {{
				background: {self.clickMarginColorHandle if self.showHitRects or drawDebugArea else "transparent"};
				/*Setting a border here messes up scrolling; scrolling goes faster than the drag does. Something in the math is off. */
				padding: -1px;
			}}
			Slider::handle:vertical {{
				image: url({"../../" if self.showHitRects else ""}assets/images/handle-bars-41x81+20.png); /* File name fields: width x height + vertical padding. */
				margin: -20px -200px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
			}}
			Slider::handle:horizontal {{
				image: url({"../../" if self.showHitRects else ""}assets/images/handle-bars-81x41+20.png); /* File name fields: width x height + horizontal padding. */
				margin: -200px -20px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
			}}
			
			Slider::groove {{
				/* This slider has an extra-large hitbox, so it's easy to tap. This is done by giving it an invisible margin. A small graphic, handle-bars.png, draws the visual slider for us. Note that the real area of the slider, and it's QWidget holders, must be as large as the hitbox.*/
				border: 1px solid black;
				margin: 20px; /* Handle needs margin to compensate for this. Controls how far from the bottom and top the groove is. */
				border-radius: 7.5px; /* Half of width. More turns it off. */
			}}
			Slider::groove:vertical {{
				width: 15px; /* The groove expands to the size of the slider by default. We'll give it an explicit width. */
			}}
			Slider::groove:horizontal {{
				height: 15px; /* The groove expands to the size of the slider by default. We'll give it an explicit width. */
			}}
		""" + self.styleSheet())
		
		
	def touchMargins(self):
		return {
			"top": 10, #cool that looks about right
			"left": 20,
			"bottom": 10,
			"right": 20,
		}
	
	def checkForVisualChange(self, evt):
		"""Change event which only fires when visual change happens.
			
			This fixes the normal valueChanged event firing 3-8 times
			per frame, when dragging the slider."""
		
		super().paintEvent(evt)
		
		val = self.value()
		if val != self.__lastValue:
			self.__lastValue = val
			self.valueChanged.emit(val)