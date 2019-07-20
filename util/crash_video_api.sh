#!/bin/bash
IFS=$'\n'
set -euxo pipefail

#Make a recording to play back.
echo | cam-json --control startRecording - > /dev/null
sleep 1
echo | cam-json --control stopRecording - > /dev/null
sleep 1

while true; do
	#Enter live mode.
	echo '{"hres": 599, "yoff": 0, "xoff": 0, "vres": 480}' | cam-json --video configure - > /dev/null
	echo '{}' | cam-json --video livedisplay - > /dev/null
	sleep 1

	#Enter playback mode.
	echo '{"xoff": 0, "yoff": 30, "vres": 361, "hres": 601}' | cam-json --video configure - > /dev/null
	echo '{"framerate": 0}' | cam-json --video playback - > /dev/null
	sleep 1
done