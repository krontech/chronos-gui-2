"""Mock for c video api. Allows easier development & testing of the QT interface.

	This mock is currently a stub. We should implement it!
"""

import sys
from debugger import *; dbg

from PyQt5.QtCore import QObject
from PyQt5.QtDBus import QDBusConnection


# Set up d-bus interface. Connect to mock system buses. Check everything's working.
if not QDBusConnection.systemBus().isConnected():
	print("Error: Can not connect to D-Bus. Is D-Bus itself running?", file=sys.stderr)
	sys.exit(-1)

class VideoMock(QObject):
	pass