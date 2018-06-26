if [ -d src/components ]; then
	PYQTDESIGNERPATH=src/components designer
else 
	if [ -d ../src/components ]; then
		PYQTDESIGNERPATH=../src/components designer
	else
		xmessage -nearmouse "Error: Couldn't find ~chronos-gui-2/src/components/."
	fi
fi