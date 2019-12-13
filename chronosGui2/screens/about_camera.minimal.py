# -*- coding: future_fstrings -*-

# Run like `python3 screens/about_camera.minimal.py` in ~src/.

import sys
from PyQt5 import uic, QtWidgets, QtCore, QtGui

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_AboutCamera 
else:
	from chronosGui2.generated.chronos import Ui_AboutCamera 

sys.path.append('widgets') #Add the components' path to import, because — since pyQt5 calculates the import path outside of our control — we can't import them from a subfolder like with the screens.


class AboutCamera(QtWidgets.QDialog, Ui_AboutCamera):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		
		self.uiDone.clicked.connect(QtWidgets.QApplication.closeAllWindows)


app = QtWidgets.QApplication(sys.argv)
app.setFont(QtGui.QFont("DejaVu Sans", 12)) #Fix fonts being just a little smaller by default than in Creator. This probably only applies to the old camApp .ui files.

aboutCamera = AboutCamera()
aboutCamera.show()

sys.exit(app.exec_())
