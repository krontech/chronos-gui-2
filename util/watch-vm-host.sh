#!/bin/bash
set -uo pipefail
IFS=$'\n'

trap "exit;" SIGINT SIGTERM #The following loop works fine in Konsole but won't ever stop on Gnome Terminal.

while true; do 
	find -regex '\./[^_\.].*' | entr -d rsync -ir . campy:~/chronos-gui --delete --links --times --inplace --exclude "__pycache__" --exclude "/.git"
done