Hello! This document contains a little listing for the utilities in this folder.

- Build Tools
	
	- watch-host.sh: Run on host to sync folder with a guest VM when files are changed.
		- example: ./utils/watch-host.sh
		- SSH and VirtualBox Shared Folders don't trigger entr on the guest OS when a file is updated. Using rsync, which does trigger entr, is simpler than writing a trigger-server. I think it's slower though, so we will probably want to write the trigger server at some point for performance reasons.
		- VirtualBox Shared Folders have issues with Make and timestamps being slightly in the future.
		- We should probably use directory mode at some point. See the bottom of `man entr` for details.
	
	- watch-guest.sh: Run on guest VM to restart the chronos-gui when files are changed.
		- example: ./utils/watch-guest.sh
		- see watch-host.sh for some context