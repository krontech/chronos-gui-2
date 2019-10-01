# -*- coding: future_fstrings -*-

# Run like `python3 screens/about_camera.minimal.py` in ~src/.

import sys
from PyQt5 import uic, QtWidgets, QtCore, QtGui
from debugger import *; dbg

sys.path.append('widgets') #Add the components' path to import, because — since pyQt5 calculates the import path outside of our control — we can't import them from a subfolder like with the screens.


class AboutCamera(QtWidgets.QDialog):
	def __init__(self):
		super().__init__()
		uic.loadUi("screens/about_camera.ui", self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		
		self.uiDone.clicked.connect(QtWidgets.QApplication.closeAllWindows)


app = QtWidgets.QApplication(sys.argv)
app.setFont(QtGui.QFont("DejaVu Sans", 12)) #Fix fonts being just a little smaller by default than in Creator. This probably only applies to the old camApp .ui files.

aboutCamera = AboutCamera()
aboutCamera.show()

sys.exit(app.exec_())