#!/bin/bash
set -euxo pipefail #enable bash's unofficial safe mode
IFS=$'\n'

#This script runs the Python-based Chronos on-board GUI.
#When a file is changed, Python is automatically restarted.
#brk() may be used in the Python script to enter an interactive debugger.

trap "{ stty sane; echo; kill 0; }" EXIT #Kill all children when we die. (This cleans up any windows lying around.) Also restore the console (keyboard stops being echoed after ctrl-c'ing out of pdb) and advance to a new line before printing the prompt again. When python is in pdb() on the camera, it will not respond to anything other than -9 unfortunately.

bash <<< "#sh doesn't do the equality test for 143, must use bash
	while true; do
		sleep 2 &
		python3 src/main.py < `readlink -f /dev/stdin` 2> `readlink -f /dev/stderr`
		PY_EXIT=\$?
		[[ \$PY_EXIT -eq 137 ]] || echo Python exited with code \$PY_EXIT. Waiting… #Python exits with 137 when killed by watchdog running pkill. We don't really care about that, since it's so frequent, but knowing when it's died of other causes is useful.
		wait #In combination with sleep 2, don't restart the python script until at least two seconds have passed since the last invocation. This stops python from running many times if python crashes immediately.
		echo; echo ----- reset -----; echo; #Visually separate logs.
	done
" 2> /dev/null & #suppress bash terminated messages caused by entr pkill
PYTHON_PARENT_SHELL=$! #Used to limit pkill to the subshell we're running our python app in. Otherwise, pkill takes out entr as well.

#Watch for filesystem changes and run a command. If another change comes in during the timeout period, ignore the first change.
python3 - $PYTHON_PARENT_SHELL << 'EOL'
# -*- coding: future_fstrings -*-
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import subprocess, sys

timeout = 0.05 #seconds

killingProcess = None

def callback(evt):
	"""Terminate running python in this session, so the bash loop above restarts it."""
	global killingProcess
	killingProcess and killingProcess.kill()
	# SIGKILL is needed only on the camera, as pdb() does not respond to SIGTERM only on the camera.
	killingProcess = subprocess.Popen(f"sleep {timeout} && pkill --signal SIGKILL --parent {sys.argv[1]} --full main.py", shell=True)
	
event_handler = PatternMatchingEventHandler(
	patterns=["*.py","*.ui","*.svg","*.png"],
	ignore_directories=True )
event_handler.on_any_event = callback
	
observer = Observer()
observer.schedule(event_handler, '.', recursive=True)
observer.start()
observer.join()
EOL