#!/bin/bash
set -uo pipefail
IFS=$'\n'

trap "exit;" SIGINT SIGTERM #The following loop works fine in Konsole but won't ever stop on Gnome Terminal.

while true; do 
	find -regex '\./[^_\.].*' | entr -d rsync -r ./ "cam:/opt/camera/chronos-gui-2/" --delete --links --rsh="/usr/bin/sshpass -p $CHRONOS_PASSWORD ssh -l root"
done