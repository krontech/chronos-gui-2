#!/bin/bash

if [ -d src/widgets ]; then
	cd src/screens #set default qt designer save location
	PYQTDESIGNERPATH=$PYQTDESIGNERPATH:../widgets PYTHONPATH=$PYTHONPATH:../ designer
else 
	if [ -d ../src/widgets ]; then
		cd ../src/screens
		PYQTDESIGNERPATH=$PYQTDESIGNERPATH:../widgets PYTHONPATH=$PYTHONPATH:../ designer
	else
		xmessage -nearmouse "Error: Couldn't find ~chronos-gui-2/src/widgets/."
	fi
fi