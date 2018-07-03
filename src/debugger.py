"""Simple, short debugging methods.

Both the provided dbg() and brk() calls are the same, calling up an interactive
command line.

Example:
	from debugger import *; dbgdbg, brk
	dbg()
"""

import sys
import pdb
from PyQt5 import QtCore


# Start our interactive debugger when an error happens.
sys.excepthook = lambda t, v, tb: (
	QtCore.pyqtRemoveInputHook(),
	pdb.traceback.print_exception(t, v, tb),
	pdb.post_mortem(t=tb)
)


@pdb.hideframe #Provided by pdbpp, which also gives colour and nice tab-completion.
def brk():
	"""Start an interactive debugger at the callsite."""
	
	QtCore.pyqtRemoveInputHook() #Prevent pyqt5 from printing a lot of errors when we take control away from it with pdb. Unfortunately, this means the app stops responding to things.
	pdb.set_trace()
	# QtCore.pyqtRestoreInputHook() #Hm, can't restore input here - since we hid this frame, I think execution continues until the end of the function. Perhaps we can subclass and call setup()? Just run it manually for now.


dbg = brk #I keep using one or the other. Either should probably work, let's make debugging easy on ourselves.


def dump(val):
	"""Print and return the value. Useful for inline print-debugging."""
	print(val)
	return val