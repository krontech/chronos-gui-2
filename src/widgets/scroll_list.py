# -*- coding: future_fstrings -*-

from PyQt5.QtCore import Qt, QSize, pyqtProperty, QItemSelectionModel
from PyQt5.QtWidgets import QListView, QScroller, QComboBox

from debugger import *; dbg
from focusable_plugin import FocusablePlugin


class ScrollList(QListView, FocusablePlugin):
	"""A scrollable list of items. Used alone or as the dropdown for a ComboBox.
		
		The scroll list also has two behaviours: If you've set
			useInlineSelectMode in Qt Designer, it acts as if it's
			holding it's children in the normal jog-wheel select flow.
			This is used on the play & save screen, since the list is
			in a menu anyway there. This mode is good for items whose
			interactions are self-contained.
		If useInlineSelectMode is not set, however, the list will behave
			like a top-level widget. Tapping in to it will let you
			select an item, and tapping again will loosen focus and let
			you select another widget.
		
		There is a second major state: That of 𝘤𝘢𝘱𝘵𝘪𝘷𝘪𝘵𝘺. A captive
			ScrollList is owned by a ComboBox, and is used as the drop-
			down by it. This behaves a little differently, because it is
			modal by nature."""
	
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self._customStyleSheet = ''
		self._useInlineSelectMode = False
		
		#Set up scroll on jogwheel.
		self.setMouseTracking(False) #Something do do with the scroller?
		self.setUniformItemSizes(True) #This enables the view to do some optimizations for performance purposes.
		self.setHorizontalScrollMode(self.ScrollPerPixel) #Make grab gesture work, otherwise moves dropdown 1 entry per pixel dragged.
		self.setVerticalScrollMode(self.ScrollPerPixel)
		self.setAttribute(Qt.WA_AcceptTouchEvents, True) #Enable touch gestures according to http://doc.qt.io/qt-5/qtouchevent.html#enabling-touch-events, which appears to be lieing.
		self.setDragDropMode(self.NoDragDrop)
		self.setMovement(self.Static)
		
		#Only works in Qt ≥ v5.10.
		#self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Enter))
		
		self.jogWheelClick.connect(self.onJogWheelClick)
		self.jogWheelLowResolutionRotation.connect(self.onJogWheelRotate)
		
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
	
	@staticmethod
	def sizeHint():
		return QSize(161, 321)
	
	def setOriginalStyleSheet(self, sheet: str):
		self._customStyleSheet = sheet
	
	def originalStyleSheet(self):
		return self._customStyleSheet
	
	@pyqtProperty(str)
	def customStyleSheet(self):
		return self._customStyleSheet
	
	@customStyleSheet.setter
	def customStyleSheet(self, styleSheet: str):
		self._customStyleSheet = styleSheet
		self.refreshStyle()
	
	@pyqtProperty(bool)
	def useInlineSelectMode(self):
		return self._useInlineSelectMode
	
	@useInlineSelectMode.setter
	def useInlineSelectMode(self, choice: bool):
		self._useInlineSelectMode = choice
	
	@property
	def isCaptive(self):
		"""A free scroll-list has different behaviour than a combo-box's 
			captive one. Primarily, it handles focus differently."""
		return isinstance(self.parent().parent(), QComboBox)
	
	@property
	def hideFocusRingFocus(self):
		return self.isCaptive or self._useInlineSelectMode
	
	@staticmethod
	def touchMargins(): #Actually needed for the focus ring to auto-calculate padding.
		return { "top":0, "left":0, "bottom":0, "right":0 }
	
	
	def onJogWheelClick(self):
		if self.isCaptive:
			comboBoxParent = self.parent().parent()
			comboBoxParent.setCurrentIndex(self.currentIndex().row())
			comboBoxParent.hidePopup()
		
		elif self._useInlineSelectMode:
			for child in self.children():
				if hasattr(child, 'injectKeystrokes'):
					child.injectKeystrokes(Qt.Key_Space)
		
		elif self.window().focusRing.isFocussedIn:
			self.window().focusRing.focusOut()
		
		else:
			self.window().focusRing.focusIn()
	
	
	def onJogWheelRotate(self, delta: int, pressed: bool):
		"""Select either the next index or the next widget."""
		if self._useInlineSelectMode:
			if (
				#No rows, always select next widget.
				self.selectionModel().currentIndex().row() == -1
				#Select previous widget, no previous list entry.
				or delta < 0 and self.selectionModel().currentIndex().row() == 0
				#Select next widget, no more list entries to select.
				or delta > 0 and self.selectionModel().currentIndex().row() == self.model().rowCount() - 1
			):
				self.selectWidget(delta)
			else:
				self.injectKeystrokes(
					Qt.Key_Up if delta < 0 else Qt.Key_Down, count=abs(delta) )
		elif pressed or self.isCaptive or self.window().focusRing.isFocussedIn:
			self.injectKeystrokes(
				Qt.Key_Up if delta < 0 else Qt.Key_Down, count=abs(delta) )
		else:
			self.selectWidget(delta)
			
	
	
	def beforeJogWheelFocus(self, delta: int):
		"""When in inline select mode, select the right end of the list to enter at."""
		if not self._useInlineSelectMode:
			return
		
		rowCount = self.model().rowCount()
		if not rowCount:
			return
			
		if delta < 0 and self.selectionModel().currentIndex().row() == 0:
			self.selectionModel().setCurrentIndex(
				self.model().index(rowCount-1, 0),
				QItemSelectionModel.ClearAndSelect )
		if delta > 0 and self.selectionModel().currentIndex().row() == rowCount - 1:
			self.selectionModel().setCurrentIndex(
				self.model().index(0,0),
				QItemSelectionModel.ClearAndSelect )
				
		
		