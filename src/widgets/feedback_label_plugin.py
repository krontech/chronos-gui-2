# -*- coding: future_fstrings -*-

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin
from plugin_settings import showHitRects

from feedback_label import FeedbackLabel


class LabelPlugin(QPyDesignerCustomWidgetPlugin):

	def __init__(self, parent=None):
		super().__init__(parent)

		self.initialized = False

	def initialize(self, core):
		if not self.initialized:
			self.initialized = True

	def isInitialized(self):
		return self.initialized

	def createWidget(self, parent):
		return FeedbackLabel(parent, showHitRects=showHitRects)

	def name(self):
		return "FeedbackLabel"

	def group(self):
		return "Chronos"

	def icon(self):
		return QIcon(QPixmap("../../assets/qt_creator/feedback_label.svg"))

	def toolTip(self):
		return """An feedback label in the Chronos style.
			
Shows text only when showError(str) or showMessage(str) is called.
Hidden by default!"""

	def whatsThis(self):
		return self.toolTip() # ¯\_(ツ)_/¯ I have no idea how to trigger this.

	def isContainer(self):
		return False

	def includeFile(self):
		return "feedback_label"
