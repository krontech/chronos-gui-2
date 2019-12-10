# -*- coding: future_fstrings -*-

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from scroll_list import ScrollList

class ScrollListPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return ScrollList(parent)

	def name(self):
		return "ScrollList"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/qt_creator/scroll_list.svg"))

	def toolTip(self):
		return """A scrollable list of items."""

	def whatsThis(self):
		return self.toolTip() #I have no idea how to trigger this. Is it the (?) window button?

	def isContainer(self):
		return False

	def includeFile(self):
		return "scroll_list"
