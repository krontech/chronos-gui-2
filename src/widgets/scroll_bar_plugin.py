from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from scroll_bar import ScrollBar


class ScrollBarPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return ScrollBar(parent, inEditor=True)

	def name(self):
		return "ScrollBar"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/qt_creator/scroll_bar.svg"))

	def toolTip(self):
		return """A scroll bar with adjustable margins.
		
Margins are displayed in Qt Designer so we can work with them. They
are hidden in the app itself, but they are still clickable. This is
important to maximize touch area, which makes the scroll bar much
more clickable."""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False

	def includeFile(self):
		return "scroll_bar"
