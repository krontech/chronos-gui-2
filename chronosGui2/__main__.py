#!/usr/bin/python3
# -*- coding: future_fstrings -*-

"""
Launch point for the Python QT back-of-camera interface.

See readme.md for more details.
"""

# General imports
import sys, os, subprocess
import time
import logging
import argparse

# QT-specific imports
from PyQt5 import QtWidgets, QtCore, QtGui
import chronosGui2.generated.assets

from chronosGui2.stats import report
from chronosGui2.debugger import *; dbg #imported for occasional use debugging, ignore "unused" warning
import chronosGui2.settings
from chronosGui2 import Hardware
from chronosGui2.main import Window

def main():
	# Do argument parsing to configure debug and logging.
	parser = argparse.ArgumentParser(description="Chronos On-Camera GUI")
	parser.add_argument('--debug', default=[], action='append', nargs='?',
			help="Enable debug logging")
	parser.add_argument('--pdb', default=False, action='store_true',
			help="Drop into a python debug console on exception")
	parser.add_argument('args', nargs=argparse.REMAINDER,
			help="Additional argument passed to Qt")
	parsed = parser.parse_args()

	# Configure logging levels.
	logging.basicConfig(
		datefmt=None,
		format='%(levelname)8s%(name)12s %(funcName)s() %(message)s',
		level=logging.INFO,
	)
	for name in parsed.debug:
		if (name == 'all'):
			logging.getLogger().setLevel(logging.DEBUG)
		else:
			logging.getLogger(name).setLevel(logging.DEBUG)

	# Install exception handlers for interactive debug on exception.
	if parsed.pdb:
		# Enable segfault backtraces, usually from C libs. (exit code 139)
		from faulthandler import enable; enable()
		
		def excepthook(t,v,tb):
			QtCore.pyqtRemoveInputHook()

			#Fix system not echoing keystrokes after first auto restart.
			try:
				os.system('stty sane')
			except Exception as e:
				pass

			pdb.traceback.print_exception(t, v, tb)
			pdb.post_mortem(t=tb)

		sys.excepthook = excepthook
		dbg, brk = pdb.set_trace, pdb.set_trace #convenience debugging
        
	# Instantiate the QApplication with any remaining arguments.
	app = QtWidgets.QApplication(parsed.args)
	app.setDoubleClickInterval(500) #400 is default and hard to do with fingers. Also this doesn't work. "The default value on X11 is 400 milliseconds", but how do you change that? Since we only use it one place, we'll just ignore it and debounce our own.

	font = QtGui.QFont("Roboto", 12)
	font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.25)
	#font.setLineSpacing(QtGui.QFont.PercentageSpacing, 120) #Not a thing. Wish it was. A line-height of 120% is used in the mockup main2.6d.svg.
	font.setHintingPreference(QtGui.QFont.PreferNoHinting) #Hinting messes up letter-spacing so badly that it's not worth it.
	app.setFont(font)

	#I don't think this is striiiiictly needed any more? Incurs 10ms penalty for slider fps.
	#eventFilter = GlobalFilter(app, window)
	#app.installEventFilter(eventFilter)

	app.setStyleSheet("""
		/* This should set line-height to roughly 120%, as specified in the mockup main2.6d.svg, but it doesn't. (It is not supported by QFont.)*/
		* {
			line-height: 35px;
		}
		
		/* Remove the little dotted focus ring. It's too hard to see, but still looks messy now that we've got our own. */
		*:focus {
			outline: 2px double blue; /*Debugging, show system focus ring.*/
			outline: none;
			outline-offset: 5px; /* This doesn't work. 😑 */
			/*outline-radius: 5px;*/
		}
	""")

	window = Window(app)
	def focusChanged(old, new):
		if new:
			window._screens[window.currentScreen].focusRing.focusOn(new)
			window._screens[window.currentScreen].focusRing.focusOut(immediate=True)
		else:
			#hide on screen transition
			window._screens[window.currentScreen].focusRing.hide()
	app.focusChanged.connect(focusChanged)


	forceHardwareInstantiation = False #This should be an env var.
	if forceHardwareInstantiation:
		hardware = Hardware()
		chronosGui2.main.connectHardwareEvents(app, hardware)
	else:
		try:
			hardware = Hardware() #Must be instantiated like this, I think the event pump timer gets eaten by GC otherwise.
			chronosGui2.main.connectHardwareEvents(app, hardware)
		except Exception:
			#We're probably in the VM, just print a message.
			print('GUI2: Could not initialize camera hardware for input.')


	report("start_up_time", {"seconds": time.perf_counter() - chronosGui2.main.perf_start_time})

	sys.exit(app.exec_())

if __name__ == "__main__":
	main()
