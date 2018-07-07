from random import randint

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from debugger import *; dbg
from touch_margin_plugin import TouchMarginPlugin, MarginWidth


class ScrollBar(QScrollBar, TouchMarginPlugin):
	Q_ENUMS(MarginWidth) #This is needed here. I don't know why the definition in the TouchMarginPlugin doesn't work.
	
	def __init__(self, parent=None, inEditor=False):
		super().__init__(parent, inEditor=inEditor)
		
		self.clickMarginColor = f"rgba({randint(0, 32)}, {randint(128, 255)}, {randint(0, 32)}, {randint(32,96)})"


	def sizeHint(self):
		return QSize(81, 201)
	
	
	def refreshStyle(self):
		if self.inEditor:
			self.setStyleSheet(f"""
				/* Editor style. Use border to show were click margin is, so we don't mess it up during layout. */
				ScrollBar, ScrollBar:vertical, ScrollBar:horizontal {{
					border-left: 1px solid black;
					/*width: 41px; /*This horribly breaks scrolling.*/
				}}
				ScrollBar::handle:vertical {{
					border: 1px solid black;
					border-radius: 0;
					background: white;
					min-height: 72px;
					image: url(assets/images/handle-bars.png);
					margin: -1px;
				}}
				/* This remvoes the bottom button by setting the height to 0px */
				ScrollBar::add-line:vertical {{
					height: 0px;
					subcontrol-position: bottom;
					subcontrol-origin: margin;
				}}
				/* This remvoes the top button by setting the height to 0px */
				ScrollBar::sub-line:vertical {{
					height: 0px;
					subcontrol-position: top;
					subcontrol-origin: margin;
				}}
				
				QSlider::groove:vertical {{
					/*This slider has an extra-large hitbox, so it's easy to tap. This is done by giving it a very large, invisible margin. A small graphic, handle-bars.png, draws the visual slider for us. Note that the real area of the slider, and it's QWidget holders, must be as large as the hitbox.*/
					border: 1px solid black;
					width: 20px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */
					background: transparent;
					margin: 20px;
					border-radius: 10px;
					padding: 0px;
				}}
				QSlider::handle:vertical {{
					background: rgba(128,128,128,0); /*Add some opacity to see the slider's actual hitbox.*/
					image: url(assets/images/handle-bars.png);
					border: 40px solid transparent;
					border-left-width: 40px;
					height: 90px;
					margin: -60px; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */
					margin-left: -60px;
					border-radius: 0px;
				}}
			""" + self.originalStyleSheet())
		else:
			self.setStyleSheet(f"""
				ScrollBar, ScrollBar:vertical, ScrollBar:horizontal {{
					border-left: 1px solid black;
					/*width: 41px; /*This horribly breaks scrolling.*/
				}}
				ScrollBar::handle:vertical {{
					border: 1px solid black;
					border-radius: 0;
					background: white;
					min-height: 72px;
					image: url(assets/images/handle-bars.png);
					margin: -1px;
				}}
				/* This remvoes the bottom button by setting the height to 0px */
				ScrollBar::add-line:vertical {{
					height: 0px;
					subcontrol-position: bottom;
					subcontrol-origin: margin;
				}}
				/* This remvoes the top button by setting the height to 0px */
				ScrollBar::sub-line:vertical {{
					height: 0px;
					subcontrol-position: top;
					subcontrol-origin: margin;
				}}
				
				/*OK, this doesn't work now. 😭*/
				QSlider::groove:vertical {{
					/*This slider has an extra-large hitbox, so it's easy to tap. This is done by giving it a very large, invisible margin. A small graphic, handle-bars.png, draws the visual slider for us. Note that the real area of the slider, and it's QWidget holders, must be as large as the hitbox.*/
					border: 1px solid black;
					width: 20px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */
					background: transparent;
					margin: 20px;
					border-radius: 10px;
					padding: 0px;
				}}
				QSlider::handle:vertical {{
					background: rgba(128,128,128,0); /*Add some opacity to see the slider's actual hitbox.*/
					image: url(assets/images/handle-bars.png);
					border: 40px solid transparent;
					border-left-width: 40px;
					height: 90px;
					margin: -60px; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */
					margin-left: -60px;
					border-radius: 0px;
				}}
			""" + self.originalStyleSheet())