import subprocess
from chronosGui2 import delay

def run(self, command: list, error: callable, success: callable, *, binaryOutput=False):
	"""Run the command, passing stdout to success.
		
		command: a list of [command, ...args]
		success: Called with stdout on a zero exit-status.
		error: Called with the exit status if 1-255.
		
		Note: This function exists because Python 3.5 grew equivalent,
			but we don't have access to it yet here in 3.4.
		
		Note: Non-static method, because something must own the QTimer
			behind delay()."""
	
	assert command and error and success
	
	proc = subprocess.Popen(
		command,
		stdout=subprocess.PIPE,
		stderr=subprocess.DEVNULL,
	)
	
	def checkProc(*, timeout):
		exitStatus = proc.poll()
		if exitStatus is None: #Still running, check again later.
			#Standard clamped exponential decay. Keeps polling to a reasonable amount, frequent at first then low.
			delay(self, timeout, lambda:
				checkProc(timeout=max(250, timeout*2)) )
		elif exitStatus:
			error(exitStatus)
		else:
			converter = (lambda x,y: x) if binaryOutput else str
			success(converter(proc.communicate()[0], 'utf8'))
	delay(self, 200, lambda: #Initial delay, df et al usually run in .17-.20s.
		checkProc(timeout=50) )