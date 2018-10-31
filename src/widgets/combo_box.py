from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt
from PyQt5.QtWidgets import QComboBox

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
#Can't directly link, because the API generally doesn't use capitalized values and our combo boxes generally do.
from focusable_plugin import FocusablePlugin

class ComboBox(QComboBox, TouchMarginPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		self.clickMarginColor = f"rgba({randint(128, 255)}, {randint(0, 32)}, {randint(0, 32)}, {randint(32,96)})"
		
		def onLowResRotate(delta, pressed):
			if pressed:
				self.injectKeystrokes(Qt.Key_Down if delta < 0 else Qt.Key_Up)
			else:
				self.selectWidget(delta)
		self.jogWheelLowResolutionRotation.connect(onLowResRotate)
		
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Space))
	
	
	def sizeHint(self):
		return QSize(181, 81)
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				ComboBox {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					font-size: 16px;
					background: white;
					
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
					border: 1px solid black;
					color: black;
					selection-background-color: grey;
				}}
				ComboBox QAbstractItemView::item {{
					padding: 10px;
					margin: 5px;
				}}

				ComboBox::drop-down {{
					width: 40px;
					border: 0px solid black;
					border-left-width: 1px;
					color: black;
					max-height: 100px;
				}}
				ComboBox::drop-down:on {{
					/*Stupid hack because the dropdown scrollbar *can't* be increased in width. It's off the width of the drop-down button by -1px. We can't just decrease the width of the drop-down button, because every other button we own is 40px instead of 39px. So. What we do is adjust the button size down when the drop-down is open, because that's the only time the off-by-one with QScrollBar is noticable, and you're distracted by the scrollbar then.*/
					padding-left: -1px;
				}}
				ComboBox::down-arrow {{
					image: url(../../assets/images/wedge-down-enabled.png);
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				ComboBox {{
					/*subcontrol-origin: padding; does nothing but mess up the drop-down button*/
					font-size: 16px;
					background: white;
					border: 1px solid black;
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
					border: 1px solid black;
					color: black;
					selection-background-color: grey;
				}}
				ComboBox QAbstractItemView::item {{
					padding: 10px;
					margin: 5px;
				}}

				ComboBox::drop-down {{
					width: 40px;
					border: 0px solid black;
					border-left-width: 1px;
					color: black;
					max-height: 100px;
				}}
				ComboBox::drop-down:on {{
					/*Stupid hack because the dropdown scrollbar *can't* be increased in width. It's off the width of the drop-down button by -1px. We can't just decrease the width of the drop-down button, because every other button we own is 40px instead of 39px. So. What we do is adjust the button size down when the drop-down is open, because that's the only time the off-by-one with QScrollBar is noticable, and you're distracted by the scrollbar then.*/
					padding-left: -1px;
				}}
				ComboBox::down-arrow {{
					image: url(assets/images/wedge-down-enabled.png);
				}}
			""" + self.originalStyleSheet())