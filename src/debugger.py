"""Simple, short debugging methods.

Both the provided dbg() and brk() calls are the same, calling up an interactive
command line.

Example:
	from debugger import dbg, brk
	dbg()
"""

import pdb
from PyQt5 import QtCore


@pdb.hideframe
def brk():
	"""Start debugging at the callsite."""
	
	QtCore.pyqtRemoveInputHook() #Prevent pyqt5 from printing a lot of errors when we take control away from it with pdb. Unfortunately, this means the app stops responding to things.
	pdb.set_trace()
	# QtCore.pyqtRestoreInputHook() #Hm, can't restore input here - since we hid this frame, I think execution continues until the end of the function. Perhaps we can subclass and call setup()? ???
	# os.system('stty sane') #restore console after pdb is done with it


dbg = brk #I keep using one or the other. Either should probably work, let's make debugging easy on ourselves.