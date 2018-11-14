from random import randint

from PyQt5.QtCore import Q_ENUMS, QSize, Qt, pyqtProperty
from PyQt5.QtWidgets import QDoubleSpinBox

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth
from direct_api_link_plugin import DirectAPILinkPlugin
from focusable_plugin import FocusablePlugin


class DecimalSpinBox(QDoubleSpinBox, TouchMarginPlugin, DirectAPILinkPlugin, FocusablePlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, showHitRects=False):
		super().__init__(parent, showHitRects=showHitRects)
		self.clickMarginColor = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(128, 255)}, {randint(32,96)})"
		self._units = ''
		
		self.jogWheelLowResolutionRotation.connect(lambda delta, pressed: 
			not pressed and self.selectWidget(delta) )
		self.jogWheelClick.connect(lambda: self.injectKeystrokes(Qt.Key_Space))


	def sizeHint(self):
		return QSize(201, 81)
	
	
	def refreshStyle(self):
		if self.showHitRects:
			self.setStyleSheet(f"""
				DecimalSpinBox {{
					/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
					font-size: 16px;
					border: 1px solid black;
					padding-right: 40px;
					padding-right: 10px;
					padding-left: 10px;
					background: rgba(255,255,255,127); /* The background is drawn under the button borders, so they are opaque if the background is opaque. */
					
					/* use borders instead of margins so we can see what we're doing */
					border-left:   {self.clickMarginLeft   * 10 + 1}px solid {self.clickMarginColor};
					border-right:  {self.clickMarginRight  * 10 + 1}px solid {self.clickMarginColor};
					border-top:    {self.clickMarginTop    * 10 + 1}px solid {self.clickMarginColor};
					border-bottom: {self.clickMarginBottom * 10 + 1}px solid {self.clickMarginColor};
				}}
				DecimalSpinBox:disabled {{ 
					color: #969696;
				}}
				DecimalSpinBox::up-button {{ 
					subcontrol-position: right; 
					right: 40px;
					image: url(../../assets/images/wedge-up-enabled.png);
				}}
				DecimalSpinBox::up-button:disabled {{ 
					image: url(../../assets/images/wedge-up-disabled.png);
				}}
				DecimalSpinBox::down-button {{ 
					subcontrol-position: right;
					image: url(../../assets/images/wedge-down-enabled.png);
				}}
				DecimalSpinBox::down-button:disabled {{ 
					subcontrol-position: right; 
					image: url(../../assets/images/wedge-down-disabled.png);
				}}
				DecimalSpinBox::up-button, DecimalSpinBox::down-button {{
					border: 0px solid black;
					border-left-width: 1px;
					width: 40px; 
					height: 40px;
					width: 0px; /*These buttons just take up room. We have a jog wheel for them.*/
					height: 0px;
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				DecimalSpinBox {{ 
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
				DecimalSpinBox:disabled {{ 
					color: #969696;
				}}
				DecimalSpinBox::up-button {{ 
					subcontrol-position: right; 
					right: 40px; 
					image: url(assets/images/wedge-up-enabled.png);
				}}
				DecimalSpinBox::up-button:disabled {{ 
					image: url(assets/images/wedge-up-disabled.png);
				}}
				DecimalSpinBox::down-button {{ 
					subcontrol-position: right; 
					image: url(assets/images/wedge-down-enabled.png);
				}}
				DecimalSpinBox::down-button:disabled {{ 
					subcontrol-position: right; 
					image: url(assets/images/wedge-down-disabled.png);
				}}
				DecimalSpinBox::up-button, DecimalSpinBox::down-button {{
					border: 0px solid black;
					border-left-width: 1px;
					width: 40px; 
					height: 40px;
					width: 0px; /*These buttons just take up room. We have a jog wheel for them.*/
					height: 0px;
				}}
			""" + self.originalStyleSheet())
	
	
	@pyqtProperty(str)
	def units(self):
		return self._units
	
	@units.setter
	def units(self, newUnitCSVList):
		self._units = newUnitCSVList