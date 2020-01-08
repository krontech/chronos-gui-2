# -*- coding: future_fstrings -*-

from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt
from PyQt5.QtWidgets import QComboBox

import chronosGui2.settings as settings
from chronosGui2.debugger import *; dbg
from theme import theme

from scroll_list import ScrollList
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
#Can't directly link, because the API generally doesn't use capitalized values and our combo boxes generally do.
from focusable_plugin import FocusablePlugin

class ComboBox(QComboBox, TouchMarginPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		
		self.theme = theme('dark')
		self.clickMarginColor = f"rgba({randint(128, 255)}, {randint(0, 32)}, {randint(0, 32)}, {randint(32,96)})"
		
		settings.observe('theme', 'dark', lambda name: (
			setattr(self, 'theme', theme(name)),
			self.refreshStyle(),
		))
		
		def onLowResRotate(delta, pressed):
			if pressed:
				self.injectKeystrokes(Qt.Key_Up if delta < 0 else Qt.Key_Down)
			else:
				self.selectWidget(delta)
		self.jogWheelLowResolutionRotation.connect(onLowResRotate)
		
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Space))
		
		#Set up the custom list view (larger, accepts tap etc)
		self.dropdown = ScrollList()
		self.setView(self.dropdown)
		
		self.__nativeDropdownSize = None
	
	def sizeHint(self):
		return QSize(181, 81)
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				ComboBox {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					color: {self.theme.text};
					font-size: 16px;
					background: {self.theme.baseInEditor}; /* The background is drawn under the button borders, so they are opaque if the background is opaque. */
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
					
					padding-left: 10px;
				}}
				ComboBox:on {{
					/*when dropdown exists*/
				}}

				ComboBox QAbstractItemView {{ /*This is the drop-down menu.*/
					border: 1px solid {self.theme.border};
					color: {self.theme.text};
					selection-background-color: {self.theme.highlight};
				}}
				ComboBox QAbstractItemView::item {{
					padding: 15px;
					background: {self.theme.base};
				}}
				ComboBox QAbstractItemView::item::selected {{
					background: {self.theme.highlight};
				}}

				ComboBox::drop-down {{
					subcontrol-origin: content;
					width: 40px;
					border: 0px solid {self.theme.border};
					border-left-width: 1px;
					color: {self.theme.text};
					max-height: 100px;
				}}
				ComboBox::drop-down:on {{
					/*Stupid hack because the dropdown scrollbar *can't* be increased in width. It's off the width of the drop-down button by -1px. We can't just decrease the width of the drop-down button, because every other button we own is 40px instead of 39px. So. What we do is adjust the button size down when the drop-down is open, because that's the only time the off-by-one with QScrollBar is noticable, and you're distracted by the scrollbar then.*/
					/*This issue is fixed in Qt 5.7, but may reappear in 5.11.*/
					/*padding-left: -1px;*/
				}}
				ComboBox::down-arrow {{
					image: url(:/assets/images/{self.theme.wedgeDownEnabled});
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				ComboBox {{
					subcontrol-origin: content;
					/*subcontrol-origin: padding; does nothing but mess up the drop-down button*/
					color: {self.theme.text};
					font-size: 16px;
					background: {self.theme.base};
					border: 1px solid {self.theme.border};
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
					padding-left: 10px;
				}}
				ComboBox:on {{
					/*when dropdown exists*/
				}}

				ComboBox QAbstractItemView {{ /*This is the drop-down menu.*/
					border: 1px solid {self.theme.border};
					color: {self.theme.text};
					selection-background-color: {self.theme.highlight};
				}}
				ComboBox QAbstractItemView::item {{
					padding: 15px;
					background: {self.theme.base}; /*Must explicitly set background colour to anything other than auto for padding to affect text position. 😠. Whyyyy.*/
					font-size: 6px; /*Doesn't work.*/
				}}
				ComboBox QAbstractItemView::item::selected {{
					background: {self.theme.highlight};
				}}
				ComboBox QScrollBar {{
					background: {self.theme.base};
					width: 8px;
					border: 1px solid {self.theme.border};
				}}
				ComboBox QScrollBar::handle {{
					background: {self.theme.highlight};
					border-radius: 3px; /*QScrollBar width - border-left - border-right / 2*/
				}}
				ComboBox QScrollBar::add-line,
				ComboBox QScrollBar::sub-line {{
					border: none;
					background: none;
				}}

				ComboBox::drop-down {{
					subcontrol-origin: content;
					width: 40px;
					border: 0px solid {self.theme.border};
					border-left-width: 1px;
					color: {self.theme.text};
				}}
				ComboBox::drop-down:on {{
					/*Stupid hack because the dropdown scrollbar *can't* be increased in width. It's off the width of the drop-down button by -1px. We can't just decrease the width of the drop-down button, because every other button we own is 40px instead of 39px. So. What we do is adjust the button size down when the drop-down is open, because that's the only time the off-by-one with QScrollBar is noticable, and you're distracted by the scrollbar then.*/
					/*This issue is fixed in Qt 5.7, but may reappear in 5.11.*/
					/*padding-left: -1px;*/
				}}
				ComboBox::down-arrow {{
					image: url(:/assets/images/{self.theme.wedgeDownEnabled});
				}}
			""" + self.originalStyleSheet())
	
	def showPopup(self):
		super().showPopup()
		
		#Only after the popup is shown do we know its native size.
		#We must cash this because size is only recomputed occasionally when shown.
		if not self.__nativeDropdownSize:
			self.__nativeDropdownSize = self.dropdown.geometry()
		
		#Adjust dropdown geometry for hit rects, because subcontrol-origin: content; doesn't work.
		margins = self.touchMargins()
		
		lineItemHeight = 50
		
		geom = self.dropdown.window().geometry()
		isBelow = geom.center().y() > self.geometry().center().y()
		geom.adjust( #Adjust position.
			margins['left'],
			-margins["bottom"] if isBelow else margins["top"],
			-margins['right'],
			-margins["bottom"] if isBelow else margins["top"], #TODO DDR 2019-01-14: make this a multiple of whatever the item size is?
		)
		
		heightAdjustment = (geom.height()-2) - (geom.height()-2)//lineItemHeight * lineItemHeight
		
		geom.adjust( #Adjust height so there's no spare whitespace.
			0, 0 if isBelow else +heightAdjustment,
			0, -heightAdjustment if isBelow else 0,
		)
		self.dropdown.window().setGeometry(geom)
