"""
Launch point for the Python QT back-of-camera interface.

Usage:
	With the camera dbus api running, run python3 cam-ui.py. Python 3.6 is
required. The dbus api, and dbus api mock, is available from the chronos-cli
repository.

See readme.md for more details.
"""

# General imports
import sys
import pdb

# QT-specific imports
from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

# cam-ui imports
import api


@pdb.hideframe
def brk():
	QtCore.pyqtRemoveInputHook() #Prevent pyqt5 from printing a lot of errors when we take control away from it with pdb. Unfortunately, this means the app stops responding to things.
	pdb.set_trace()
	# QtCore.pyqtRestoreInputHook() #Hm, can't restore input here - since we hid this frame, I think execution continues until the end of the function.
	# os.system('stty sane') #restore console after pdb is done with it


QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)



class Ui(QtWidgets.QDialog):
	def __init__(self):
		super(Ui, self).__init__()
		uic.loadUi('assets/layouts/cammainwindow.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowOpacity(0.5)
		self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Button binding.
		self.cmdDebugWnd.clicked.connect(self.printExposureNs)
		
		self.show()
	
	@pyqtSlot() #Not strictly needed - see http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html#the-pyqtslot-decorator for details.
	def printExposureNs(self) -> None:
		print("exposure is %ins" % api.control('get_video_settings')["exposureNsec"])


if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
	
	window = Ui()
	window.show()
	
	sys.exit(app.exec_())