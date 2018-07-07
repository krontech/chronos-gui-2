from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin

from radio_button import RadioButton


class RadioButtonPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return RadioButton(parent, inEditor=True)

	def name(self):
		return "RadioButton"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/qt_creator/radio_button.svg"))

	def toolTip(self):
		return """A radio button with adjustable margins.
		
Margins are displayed in Qt Designer so we can work with them. They
are hidden in the app itself, but they are still clickable. This is
important to maximize touch area, which makes the radio button much
more clickable."""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False

	def includeFile(self):
		return "radio_button"
