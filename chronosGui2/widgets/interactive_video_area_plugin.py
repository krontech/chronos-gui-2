# -*- coding: future_fstrings -*-

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin
from plugin_settings import showHitRects

from interactive_video_area import InteractiveVideoArea


class InteractiveVideoAreaPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return InteractiveVideoArea(parent, showHitRects=showHitRects)

	def name(self):
		return "InteractiveVideoArea"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/qt_creator/interactive_video_area.svg"))

	def toolTip(self):
		return """A white panel, to cover the video presentation layer when needed.

Video comes from the FPGA via OMX, I think. It gets put under the
framebuffer, which our UI is rendered to. Since we need to see the
video, we need to have a way to make a hole in our app. However, we
don't want to have the "doughnut" around the hole to hold subwidgets,
which is why we don't just use a plain widget styled white here."""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False #No subwidgets. This is just background paneling. 

	def includeFile(self):
		return "interactive_video_area"
