from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from button import Button


class ButtonPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return Button(parent, inEditor=True)

	def name(self):
		return "Button"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/images/qt_creator_icons/button.svg"))

	def toolTip(self):
		return "chronos standard button"

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯

	def isContainer(self):
		return False

	def includeFile(self):
		return "button"
