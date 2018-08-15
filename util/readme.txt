Hello! This document contains a little listing for the utilities in this folder.

For how these utilities are used, see readme.html in the root folder of this project.

Note: ~ denotes "in the root folder of" this project. So, this file is ~util/readme.txt. I've rolled with this notation, as opposed to ~/*, because the previous one probably won't resolve to anything if you don't understand it. It's a bit less dangerous that way. ☺

- Build Tools

	- chronos-designer-template.ui: Start new screens with this template. It's an empty shell with a few convenient things already filled in, such as a white background and a window title for the VM.
	
	- com.krontech.chronos.conf: Configuration file for D-Bus, to allow the service to start. See it for installation instructions.
	
	- designer.sh: Launch QT Designer via this script, to set the correct env var so you get the custom widgets the UI uses.
	
	- fbdev.py: Example script for accessing the linux framebuffer.
	
	- watch-*.sh: Optional scripts which handle automatic redeployment of the app.
		- watch-camera.sh: Run util/watch-camera.sh on the camera, in the root folder of the project, to automatically start the app when changes are made to its source.
		- watch-computer.sh: Watch for and upload changed files to the camera. Run util/watch-computer.sh on your computer, in the root folder of the project. Companion to watch-camera.sh
		- watch-vm-guest: Similar to watch-camera.sh, but for use in a virtual machine.
		- watch-vm-host: Similar to watch-computer.sh, but uploads to a virtual machine rather than the physical camera.