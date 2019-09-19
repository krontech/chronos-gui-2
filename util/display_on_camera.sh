#!/bin/bash
set -euf -o pipefail
trap "exit 0" INT

#Display an image on the Chronos.
{
	convert -size 800x480 -depth 8 $1 bgra:-; 
	sleep infinity; #sleep to hold /dev/fb0 open
} | ssh cam "cat - > /dev/fb0"