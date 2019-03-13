# -*- coding: future_fstrings -*-

"""Simple, short debugging methods.

Both the provided dbg() and brk() calls are the same, calling up an interactive
command line.

Example:
	from debugger import *; dbg
	dbg()
"""

import sys
import pdb
from PyQt5 import QtCore
from os import system


# Start our interactive debugger when an error happens.
def eh(t,v,tb):
	QtCore.pyqtRemoveInputHook()
	
	#Fix system not echoing keystrokes after first auto restart.
	try:
		system('stty sane')
	except Exception as e:
		pass
	
	pdb.traceback.print_exception(t, v, tb)
	pdb.post_mortem(t=tb)
sys.excepthook = eh


def brk():
	"""Start an interactive debugger at the callsite."""
	
	QtCore.pyqtRemoveInputHook() #Prevent pyqt5 from printing a lot of errors when we take control away from it with pdb. Unfortunately, this means the app stops responding to things.
	pdb.set_trace()
	# QtCore.pyqtRestoreInputHook() #Hm, can't restore input here - since we hid this frame, I think execution continues until the end of the function. Perhaps we can subclass and call setup()? Just run it manually for now.

# @pdb.hideframe #Provided by pdbpp, which also gives color and nice tab-completion.
# pdbpp segfaults Designer on my desktop computer, but works on my laptop so we'll only use it if available.
if hasattr(pdb, 'hideframe'):
	brk = pdb.hideframe(brk)

dbg = brk #I keep using one or the other. Either should probably work, let's make debugging easy on ourselves.


def dump(*args):
	"""Print and return the value. Useful for inline print-debugging.
		
		1-arity: dump(val: any)
			print val and return it.
		2-arity: dump(label, val)"""
	if not args:
		raise ValueError('No args specified to dump!')
	print(*args)
	return args[0] if len(args) == 1 else args[1]
	

def breakIf(widget):
	"""If a keyboard modifier is held, start an interactive debugger.
		
		Args:
			widget: A Qt Widget, in a GUI2 screen which has app set
				to the global application variable. The application
				variable gets the keyboard modifier state.
	
		Useful for debugging input-driven events going off the rails
			half-way through. Note that due to the call to
			pyqtRemoveInputHook in brk(), this is only a trigger-on
			deal. You can't stop triggering it.
		"""
	
	if int(widget.parent().app.keyboardModifiers()) != QtCore.Qt.NoModifier: #33554432: #heck if I know
		brk()

if hasattr(pdb, 'hideframe'):
	breakIf = pdb.hideframe(breakIf)