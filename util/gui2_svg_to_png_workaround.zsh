#!/usr/bin/zsh

#Convert SVG to PNG to work around QT incorrectly using viwebox as actual size. Fixed somewhere after QT 5.7 and before QT 5.10, inclusive.
mogrify -format png -background none assets/images/**/*.svg