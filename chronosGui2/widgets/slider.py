# -*- coding: future_fstrings -*-

from random import randint
import time

from PyQt5.QtCore import QSize, Qt, pyqtSignal, QObject, QRect, QPoint
from PyQt5.QtWidgets import QSlider
from PyQt5.QtGui import QRegion, QPaintEvent

import chronosGui2.settings as settings
from theme import theme

from focusable_plugin import FocusablePlugin
from show_paint_rect_plugin import ShowPaintRectsPlugin


class Slider(ShowPaintRectsPlugin, FocusablePlugin, QSlider): #Must be in this order, because QSlider doesn't propagate a super() chain.
	"""Styled, focussable QSlider. Contains fixed valueChanged event.
		
		When overriding self.paintEvent, always make sure to call
		self.checkForVisualChange.
		
		Use debounce.valueChanged and debounce.sliderMoved signals 
		instead of their unpostfixed versions. The unpostfixed versions
		fire too often."""
	
	class Debounce(QObject):
		"""Less frequent version of parent valueChanged and sliderMoved.
		
			Only fired once per frame, not "12 times between frames" as
			per the default."""
		
		valueChanged = pyqtSignal(int)
		sliderMoved = pyqtSignal(int) #Naming this "sliderMoved" stops QSliderTap from working for some reason. We cannot possibly to the parent signal if we subclass it.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent)
		
		self.setAttribute(Qt.WA_OpaquePaintEvent, True)
		
		self.theme = theme('dark')
		self.showHitRects = showHitRects
		
		self.clickMarginColorSlider = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
		self.clickMarginColorHandle = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"
		
		self.baseStyleSheet = self.styleSheet()
		settings.observe('theme', 'dark', lambda name: (
			setattr(self, 'theme', theme(name)),
			self.refreshStyle(),
		))
		
		self.isFocused = False
		self.jogWheelClick.connect(self.toggleFocussed)
		self.jogWheelLowResolutionRotation.connect(self.onLowResRotate)
		
		self.debounce = Slider.Debounce()
		
		self._userGeneratedEvent = False #Set to true when sliderMoved happens.
		def updateUserGeneratedEvent():
			self._userGeneratedEvent = True
		self.sliderMoved.connect(updateUserGeneratedEvent)
		
		self.beingHeld = False #Set to true when sliderMoved happens.
		def tapPressed():
			self.beingHeld = True
		self.sliderPressed.connect(tapPressed)
		def tapReleased():
			self.beingHeld = False
		self.sliderReleased.connect(tapReleased)
		
		self.__lastValue = self.value()
		self._fpsMonitorLastFrame = time.perf_counter()
		
		self.setContentsMargins(30, 10, 30, 10) #rough guess, good enough?
		
		#Move the focus ring with the slider.
		self.rangeChanged.connect(self.tryRefocus)
		self.focusGeometryNudge = (0,0,0,0) #xywh tuple to move the focus ring to be aligned. Different sliders have different nudges, and I can't figure out why.

	def sizeHint(self):
		return QSize(81, 201)
	
	def keyPressEvent(self, evt):
		self._userGeneratedEvent = True
		return super().keyPressEvent(evt)
		
	def wheelEvent(self, evt):
		self._userGeneratedEvent = True
		return super().wheelEvent(evt)
	
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
				image: url({"../../" if self.showHitRects else ""}assets/images/{self.theme.slider.verticalHandle}); /* File name fields: width x height + vertical padding. */
				margin: -20px -200px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
			}}
			Slider::handle:horizontal {{
				image: url({"../../" if self.showHitRects else ""}assets/images/{self.theme.slider.horizontalHandle}); /* File name fields: width x height + horizontal padding. */
				margin: -200px -20px; /* y: -slider groove margin. x: touch padding outsidet the groove. Clipped by Slider width. Should be enough for most customizations if we move stuff around. */
			}}
			
			Slider::groove {{
				/* This slider has an extra-large hitbox, so it's easy to tap. This is done by giving it an invisible margin. A small graphic, handle-bars.png, draws the visual slider for us. Note that the real area of the slider, and it's QWidget holders, must be as large as the hitbox.*/
				border: 1px solid {self.theme.border};
				margin: 20px; /* Handle needs margin to compensate for this. Controls how far from the bottom and top the groove is. */
				border-radius: 7.5px; /* Half of width. More turns it off. */
				background-color: {self.theme.base};
			}}
			Slider::groove:vertical {{
				width: 15px; /* The groove expands to the size of the slider by default. We'll give it an explicit width. */
			}}
			Slider::groove:horizontal {{
				height: 15px; /* The groove expands to the size of the slider by default. We'll give it an explicit width. */
			}}
		""" + self.baseStyleSheet)
		
		
	def touchMargins(self):
		return {
			"top": 10, #cool that looks about right
			"left": 30,
			"bottom": 10,
			"right": 30,
		}
	
	def visibleRegion(self):
		return QRegion(
			self.getContentsMargins()[0],
			self.getContentsMargins()[1],
			self.width() - self.getContentsMargins()[0] - self.getContentsMargins()[2],
			self.height() - self.getContentsMargins()[1] - self.getContentsMargins()[3],
		)
	
	def focusGeometry(self, padding):
		focusGeometryMargin = QSize(padding,padding)
		range_ = self.maximum() - self.minimum() or 1
		adjustPct = range_ and self.value() / range_ - 0.5 #±50% of range
		pos = self.rect().center()
		sliderSize = self.sliderSize()
		if self.width() < self.height():
			sliderPlay = self.height() - self.touchMargins()['top'] - self.touchMargins()['bottom'] - sliderSize.height()
			pos = pos + QPoint(0, round(-adjustPct * sliderPlay))
		else:
			sliderPlay = self.width() - self.touchMargins()['left'] - self.touchMargins()['right'] - sliderSize.width()
			pos = pos + QPoint(round(adjustPct * sliderPlay), 0)
		
		pos = self.mapToGlobal(pos)
		return QRect(
			pos.x() - sliderSize.width()/2 - focusGeometryMargin.width() + self.focusGeometryNudge[0],
			pos.y() - sliderSize.height()/2 - focusGeometryMargin.height() + self.focusGeometryNudge[1],
			sliderSize.width() + focusGeometryMargin.width()*2 + self.focusGeometryNudge[2],
			sliderSize.height() + focusGeometryMargin.height()*2 + self.focusGeometryNudge[3],
		)
	
	def sliderSize(self):
		return QSize(40, 80) if self.width() < self.height() else QSize(80, 40)
	
	#Neither of these seem to be overridable, they never get called. If they
	#were called, we could use update() to not cause the main menu buttons to
	#repaint because they're above the slider touch margin.
	#def rect(self):
	#	print('update rect')
	#	return QRect(30, 10, self.width()-30, self.height-10)
	#
	#def update(arg):
	#	print('update event', arg)
	#	return 
	
	def paintEvent(self, evt):
		"""Change event which only fires when visual change happens.
			
			This fixes the normal valueChanged event firing 3-8 times
			per frame, when dragging the slider."""
		
		
		#print('frame draw time', time.perf_counter()-self._fpsMonitorLastFrame, 'sec')
		self._fpsMonitorLastFrame = time.perf_counter()
		
		clippedEvt = QPaintEvent(self.visibleRegion())
		super().paintEvent(clippedEvt)
		
		val = self.value()
		if val != self.__lastValue:
			self.__lastValue = val
			self.debounce.valueChanged.emit(val)
			if self._userGeneratedEvent:
				self._userGeneratedEvent = False
				self.debounce.sliderMoved.emit(val)
			
			#Move the focus ring with the slider.
			self.tryRefocus()
	
	
	def onLowResRotate(self, delta, pressed):
		if self.isFocused:
			if pressed:
				self.injectKeystrokes(
					Qt.Key_PageUp if delta > 0 else Qt.Key_PageDown,
					count=abs(delta) )
			else:
				self.injectKeystrokes(
					Qt.Key_Up if delta > 0 else Qt.Key_Down,
					count=abs(delta) )
		else:
			if pressed:
				self.injectKeystrokes(
					Qt.Key_PageUp if delta > 0 else Qt.Key_PageDown,
					count=abs(delta) )
			else:
				self.selectWidget(delta)
	
	
	def toggleFocussed(self):
		self.isFocused = not self.isFocused
		if self.isFocused:
			self.window().focusRing.focusIn()
		else:
			self.window().focusRing.focusOut()
	
	def tryRefocus(self, *_):
		try:
			self.window().focusRing.refocus()
		except AttributeError:
			pass #No focus ring yet. There will be. :)