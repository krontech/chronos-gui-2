# -*- coding: future_fstrings -*-

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin
from plugin_settings import showHitRects

from storage_media_select import StorageMediaSelect

from focusable_plugin import FocusablePlugin

class StorageMediaSelectPlugin(QPyDesignerCustomWidgetPlugin, FocusablePlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return StorageMediaSelect(parent, showHitRects=showHitRects)

	def name(self):
		return "StorageMediaSelect"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap(":/assets/qt_creator/storage_media_select.svg"))

	def toolTip(self):
		return """Select a partition on an external drive."""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False

	def includeFile(self):
		return "storage_media_select"
