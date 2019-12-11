# -*- coding: future_fstrings -*-

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin
from plugin_settings import showHitRects

from subheader import Subheader


class SubheaderPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return Subheader(parent, showHitRects=showHitRects)

	def name(self):
		return "Subheader"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap(":/assets/qt_creator/subheader.svg"))

	def toolTip(self):
		return """A subheader - above label but below header
in importance - in the Chronos style."""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False

	def includeFile(self):
		return "subheader"