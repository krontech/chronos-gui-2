Hello! This document contains a little listing for the utilities in this folder.

For content on how these utilities are intended to be used, see readme.html in the root folder of this project.

Note: ~ denotes "in the root folder of" this project. So, this file is ~util/readme.txt. I've rolled with this notation, as opposed to ~/*, because the previous one probably won't resolve to anything if you don't understand it. It's a bit less dangerous that way. ☺

- Build Tools
	- Anaconda.sublime-settings: Python Pep8 listing ignore ruleset. Our project is shaped much differently than core Python is, so we have a different ruleset.
	
	- ca.krontech.chronos.conf: Configuration file for D-Bus, to allow the service to start. See it for installation instructions.
	
	- Camera *.sgrd: Tabs for KDE System Monitor. Open with File → Import Tab From File… on your computer. Requires `SSH cam` to be set up.
	
	- chronos-designer-template.ui: Start new screens with this template. It's an empty shell with a few convenient things already filled in, such as a white background and a window title for the VM.
	
	- chronos-gui-2-dev.service: systemd service file for dev install to ~/gui.
	
	- chronos-gui2.conf: Snippet of bash script which sets some env vars to let the gui run.
	
	- crash_video_api.sh: Just what it says on the tin. Reproduction for a standing bug.
	
	- creator.sh: Backup if designer.sh doesn't work. Launch Qt Creator via this script, to set the correct env var so you get the custom widgets the UI uses.
	
	- deploy-fonts.sh: Copy fonts from ../assets to the camera, so our UI can use them.
	
	- designer.sh: Launch Qt Designer via this script, to set the correct env vars so you get the custom widgets the UI uses.
		- Requires Qt Designer and the PyQt5 tools to be installed. On Ubuntu, this is:
			> sudo apt install python3-pip qttools5-dev-tools qt5-default pyqt5-dev-tools
			> pip3 install PyQt5==5.10.1 future_fstrings==1.2.0
			- You may isolate this by using `python3 -m venv venv`, which is provided by `sudo apt install python3-venv`.
		- You will see some errors along the lines of "Unable to import api". It is nonfatal, just some of our plugins reporting that they can't find the Chronos control api software. They'll work fine when they're on the camera.
	
	- display_on_camera.sh: Display an image on the camera. The input can be anything imagemagick understands. (Obtainable by `sudo apt install imagemagick` on Linux.)
	
	- fbdev.py: Example script for accessing the linux framebuffer. (Runs on camera.)
	
	- gui2_svg_to_png_workaround.zsh: Convert an SVG image to a PNG, because our web planning tool and our chat tool really don't ingest SVG well.
	
	- readme.txt: You're soaking in it.
	
	- reset-triggers-to-normal-mode.sh: Run on the camera to reset trigger/io to something sane.
	
	- screenshot_camera.sh: Capture an image from the back of camera display. Requires `ssh cam` to be set up, as well as imagemagick and gimp.
	
	- start_record_sequence.sh: Start a record sequence using the API's soft trigger system. This is a reproduction for a standing bug.
	
	- start_up_time_csv.sh: Example script for parsing the stats reported by the camera to stats*, documented below. (Data is only captured on the internal network in Krontech, don't worry. 😉)
	
	- stats*: Collect stats from dev machines. Used primarily to profile performance problems.
		- stats.node.js: The stats server, collecting data and writing it to stats_reported/. Launch with `node stats.node.js`.
		- stats_reported/: Performance stats collected by stats.node.js.
		- stats.html: Viewer for stats_reported/ data.
	
	- ts.conf: Typescript config for stats.node.js.
	
	- watch-*.sh: Optional scripts which handle automatic redeployment of the app.
		- Requires `apt install entr rsync ssh-askpass`.
		- watch-camera.sh: Run util/watch-camera.sh on the camera, in the root folder of the project, to automatically start the app when changes are made to its source.
		- watch-computer.sh: Watch for and upload changed files to the camera. Run util/watch-computer.sh on your computer, in the root folder of the project. Companion to watch-camera.sh
		- watch-vm-guest: Similar to watch-camera.sh, but for use in a virtual machine.
		- watch-vm-host: Similar to watch-computer.sh, but uploads to a virtual machine rather than the physical camera.
		