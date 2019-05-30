"""Configure logging for GUI2.

	Log levels are:
		CRITICAL 50
		ERROR    40
		WARNING  30 Generally we always want to leave warnings on.
		PRINT    25 For println-style debugging. Always temporary!
		INFO     20
		DEBUG    10
		NOTSET   00
"""

import logging

#Use closure to avoid polluting module namespace.
def setUpLogging():
	PRINT_LEVEL = 25
	logging.addLevelName(PRINT_LEVEL, "PRINT")
	def print_(self, message, *args, **kws):
		if self.isEnabledFor(PRINT_LEVEL):
			self._log(PRINT_LEVEL, message, args, **kws) 
	logging.Logger.print = print_
	
	
	logging.basicConfig(
		datefmt='',
		format='%(levelname)8s %(name)12s [%(funcName)s]: %(message)s',
		level=logging.INFO,
	)
	
	# pyqt5 uic prints a looooot of DEBUG messages.
	logging.getLogger('PyQt5.uic.uiparser').setLevel(logging.INFO)
	logging.getLogger('PyQt5.uic.properties').setLevel(logging.INFO)
	
	#Turn on and off logging for various components here.
	#I think you hold logging like this: The named logger is used for
	#when you want to turn on and off various components. The level
	#is used to determine how much of the component you want to hear.
	#Since you can't turn off a specific log level, only set the
	#level above which to log, it's not appropriate to define a
	#custom log level for each of the components because we'd have to
	#sort the components by importance. Which doesn't make any sense.
	logging.getLogger('Chronos.gui').setLevel(logging.DEBUG) #GUI, having to do with the QT GUI code. Catchall for the other two categories, since everything is in service of the GUI here.
	logging.getLogger('Chronos.api').setLevel(logging.DEBUG) #The API client logging. This 
	logging.getLogger('Chronos.perf').setLevel(logging.WARNING)
	
	#logging.disable(PERF_LEVEL) #Don't need this until it starts acting up.
	#logging.getLogger('gui2')

setUpLogging()
del setUpLogging