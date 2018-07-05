from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from header_label import HeaderLabel


class HeaderLabelPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return HeaderLabel(parent, inEditor=True)

	def name(self):
		return "HeaderLabel"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/images/qt_creator_icons/button.svg"))

	def toolTip(self):
		return """A section header in the Chronos style.

Basically a label with a bigger font."""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False

	def includeFile(self):
		return "header_label"
