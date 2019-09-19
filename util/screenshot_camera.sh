#!/bin/bash
set -euf -o pipefail

ssh cam "cat /dev/fb0 | head --bytes=1536000" | #Use head to limit fb0 to actual screen data, convert gets very confused otherwise. Use remote's head because ssh dies with 255 otherwise.
convert -size 800x480 -depth 8 bgra:- /tmp/screenshot.png #Regular files must be used, gimp can't handle other ones such as stdin or named pipes.
gimp /tmp/screenshot.png