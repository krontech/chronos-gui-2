#!/bin/bash
set -euo pipefail
IFS=$'\n'

trap "exit;" SIGINT SIGTERM

cd "$(dirname "$0")/.." #Always sync project root directory.

#The following loop works fine in Konsole but won't ever stop on Gnome Terminal.
while true; do 
	find -regex '\./[^_\.].*' ! -name git_description ! -path 'util/stats_reported' | entr -d bash -c "
		if [[ \$(cat git_description) != \$(git describe --tags --always) ]]; then #Only update when description changes, results in some thrashing otherwise when using --times.
			git describe --tags --always > git_description
		fi
		
		#Use --times instead of --checksum because it means we can touch a file (ie, save it) and have the camera script restart. Checksum is more proper, and may take longer to run, but I haven't noticed any difference in my testing. Note that with --times, we redeploy the whole project when we switch computers, because we ran 'git checkout' at different times.
		rsync --recursive --delete --links --inplace --times --itemize-changes \
			./ \"${CAM_ADDRESS:-root@192.168.12.1}:~/gui/\" \
			--exclude \"__pycache__\" \
			--exclude \"/.git\" \
			--exclude \".mypy_cache\" \
			--exclude \"util/stats_reported\" \
			--exclude \"src/read_jog_wheel_encoder\" \
			--exclude \".directory\" \
	" || true
done