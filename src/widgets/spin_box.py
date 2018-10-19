from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize
from PyQt5.QtWidgets import QSpinBox

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from direct_api_link_plugin import DirectAPILinkPlugin
from focusable_plugin import FocusablePlugin


class SpinBox(QSpinBox, TouchMarginPlugin, DirectAPILinkPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		self.clickMarginColor = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(128, 255)}, {randint(32,96)})"
		
		#Jog wheel-based state.
		self.isFocussed = False
		self.jogWheelMagnitude = 0
		
		def onLowResRotate(delta, pressed):
			if not self.isFocussed:
				if pressed:
					self.injectKeystrokes(Qt.Key_Down if delta < 0 else Qt.Key_Up)
				else:
					self.selectWidget(delta)
			else:
				if pressed:
					#select the place
					pass
				else: 
					self.injectKeystrokes(Qt.Key_Down if delta < 0 else Qt.Key_Up)
		self.jogWheelLowResolutionRotation.connect(onLowResRotate)
		
		def toggleFocussed():
			self.isFocussed = not self.isFocussed
		self.jogWheelClick.connect(toggleFocussed)


	def sizeHint(self):
		return QSize(201, 81)
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				SpinBox {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					font-size: 16px;
					border: 1px solid black;
					padding-right: 40px;
					padding-left: 10px;
					background: white;
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
				SpinBox:disabled {{ 
					color: #969696;
				}}
				SpinBox::up-button {{ 
					subcontrol-position: right; 
					right: 40px; 
					image: url(../../assets/images/wedge-up-enabled.png);
				}}
				SpinBox::up-button:disabled {{ 
					image: url(../../assets/images/wedge-up-disabled.png);
				}}
				SpinBox::down-button {{ 
					subcontrol-position: right; 
					image: url(../../assets/images/wedge-down-enabled.png);
				}}
				SpinBox::down-button:disabled {{ 
					subcontrol-position: right; 
					image: url(../../assets/images/wedge-down-disabled.png);
				}}
				SpinBox::up-button, SpinBox::down-button {{
					border: 0px solid black;
					border-left-width: 1px;
					width: 40px; 
					height: 40px;
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				SpinBox {{ 
					border: 1px solid black;
					padding-right: 40px;
					padding-left: 10px;
					font-size: 16px;
					background: white;
					
					/* Add some touch space so this widget is easier to press. */
					margin-left: {self.clickMarginLeft*10}px;
					margin-right: {self.clickMarginRight*10}px;
					margin-top: {self.clickMarginTop*10}px;
					margin-bottom: {self.clickMarginBottom*10}px;
				}}
				SpinBox:disabled {{ 
					color: #969696;
				}}
				SpinBox::up-button {{ 
					subcontrol-position: right; 
					right: 40px; 
					image: url(assets/images/wedge-up-enabled.png);
				}}
				SpinBox::up-button:disabled {{ 
					image: url(assets/images/wedge-up-disabled.png);
				}}
				SpinBox::down-button {{ 
					subcontrol-position: right; 
					image: url(assets/images/wedge-down-enabled.png);
				}}
				SpinBox::down-button:disabled {{ 
					subcontrol-position: right; 
					image: url(assets/images/wedge-down-disabled.png);
				}}
				SpinBox::up-button, SpinBox::down-button {{
					border: 0px solid black;
					border-left-width: 1px;
					width: 40px; 
					height: 40px;
				}}
			""" + self.originalStyleSheet())