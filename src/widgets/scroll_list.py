# -*- coding: future_fstrings -*-

from PyQt5.QtCore import Qt, QSize, pyqtProperty
from PyQt5.QtWidgets import QListView, QScroller

from debugger import *; dbg
from focusable_plugin import FocusablePlugin


class ScrollList(QListView, FocusablePlugin):
	"""A scrollable list of items. Used alone or as the dropdown for a ComboBox.
		
		Provides custom styling & behaviour, most notably for jog wheel
		interaction."""
	
	
	#TODO DDR 2019-01-14: Make smoothly scrollable via https://forum.qt.io/topic/96010/scroll-items-by-using-touching-dragging-without-using-scrollbar-in-qscrollarea/3
	
	hideFocusRingFocus = True
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self._customStyleSheet = ''
		
		#Set up scroll on jogwheel.
		self.setMouseTracking(False) #Something do do with the scroller?
		self.setUniformItemSizes(True) #This enables the view to do some optimizations for performance purposes.
		self.setHorizontalScrollMode(self.ScrollPerPixel) #Make grab gesture work, otherwise moves dropdown 1 entry per pixel dragged.
		self.setVerticalScrollMode(self.ScrollPerPixel)
		self.setAttribute(Qt.WA_AcceptTouchEvents, True) #Enable touch gestures according to http://doc.qt.io/qt-5/qtouchevent.html#enabling-touch-events, which appears to be lieing.
		
		self.jogWheelLowResolutionRotation.connect(lambda delta:
			self.injectKeystrokes(
				Qt.Key_Up if delta < 0 else Qt.Key_Down, count=abs(delta) ) )
		
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Enter))
		
		#Add drag-to-scroll to dropdown menus.
		QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture) #DDR 2019-01-15: Defaults to TouchGesture - which should work, according to WA_AcceptTouchEvents, but doesn't.
		scroller = QScroller.scroller(self.viewport())
		properties = scroller.scrollerProperties()
		properties.setScrollMetric(properties.AxisLockThreshold, 0.0)
		properties.setScrollMetric(properties.DragStartDistance, 0.003) #default: 0.005 - tweaked for "feel", the platform defaults are overly dramatic.
		properties.setScrollMetric(properties.OvershootDragDistanceFactor, 0.3) #default: 1
		properties.setScrollMetric(properties.OvershootScrollDistanceFactor, 0.3) #default: 1
		properties.setScrollMetric(properties.OvershootScrollTime, 0.5) #default: 0.7
		scroller.setScrollerProperties(properties)
		
		self.refreshStyle()
		
	def refreshStyle(self):
		self.setStyleSheet(f"""
			QAbstractItemView {{
				border: 1px solid black;
				color: black;
				selection-background-color: grey;
			}}
			QAbstractItemView::item {{
				padding: 15px;
				background: white; /*Must explicitly set background colour to anything other than auto for padding to affect text position. 😠. Whyyyy.*/
				font-size: 6px; /*Doesn't work.*/
			}}
			QAbstractItemView::item::selected {{
				background: #888;
			}}
			
			QScrollBar {{
				background: white;
				width: 8px;
				border: 1px solid white;
			}}
			QScrollBar::handle {{
				background: #666;
				border-radius: 3px; /*QScrollBar width - border-left - border-right / 2*/
			}}
			QScrollBar::add-line,
			QScrollBar::sub-line {{
				border: none;
				background: none;
			}}

			ScrollList::drop-down {{
				subcontrol-origin: content;
				width: 40px;
				border: 0px solid black;
				border-left-width: 1px;
				color: black;
			}}
			ScrollList::drop-down:on {{
				/*Stupid hack because the dropdown scrollbar *can't* be increased in width. It's off the width of the drop-down button by -1px. We can't just decrease the width of the drop-down button, because every other button we own is 40px instead of 39px. So. What we do is adjust the button size down when the drop-down is open, because that's the only time the off-by-one with QScrollBar is noticable, and you're distracted by the scrollbar then.*/
				padding-left: -1px;
			}}
			ScrollList::down-arrow {{
				image: url(assets/images/wedge-down-enabled.png);
			}}
		""" + self.originalStyleSheet())
	
	def sizeHint(self):
		return QSize(161, 321)
	
	def setOriginalStyleSheet(self, sheet):
		self._customStyleSheet = sheet
	
	def originalStyleSheet(self):
		return self._customStyleSheet
	
	@pyqtProperty(str)
	def customStyleSheet(self):
		return self._customStyleSheet
	
	@customStyleSheet.setter
	def customStyleSheet(self, styleSheet):
		self._customStyleSheet = styleSheet
		self.refreshStyle()