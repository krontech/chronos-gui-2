#!/bin/bash
set -euo pipefail #enable bash's unofficial safe mode
IFS=$'\n'

echo "Setting up camera for GUI development."

echo "Updating system packages."
apt update && apt-get upgrade --yes

echo "Updating certs."
apt install ca-certificates --yes

echo "Installing common utilities."
apt install vim rsync curl --yes

if systemctl disable chronos-gui2; then
    echo "Disabling chronos-gui2 autostart."
else
    echo "Failed to disable chronos-gui2 autostart. Make sure to stop the running UI before starting a new one!"
fi

read -p "Optional: Install watch script dependancies and nicer debugging? (This will upgrade Pip.) Y/n" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Installing."
    apt install python3-pip --yes
    pip3 install --upgrade setuptools==41.0.1 #Required for pdbpp.
    pip3 install pdbpp==0.10.0 watchdog==0.9.0 #Optional deps. "pdbpp" provides improvements to pdb, Python's interactive debugger. "watchdog" provides watchmedo, used for automatic reload with util/watch-camera.sh.
    mkdir --parents ~/gui ~/web
else
    echo "Skipped."
fi

if [ -f ~/.pdbrc ]; then
    echo "Skipping setting up .bashrc and .pdbrc; they already seem to be set up."
else
    echo "Setting up .bashrc and .pdbrc to provide environment for Python."
    cat >> ~/.bashrc <<'EOL'

#env vars required by QT to run, display, and be touched:
export QSG_RENDER_LOOP=basic
export QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0
export QT_QPA_GENERIC_PLUGINS=tslib:/dev/input/event0

#Make Python 3.4 not choke on unicode characters.
export PYTHONIOENCODING=utf-8

#Set the camera to use utf8, to avoid extraneous escape sequences in `systemctl status`.
export LC_CTYPE=en_US.utf8

#Set API into mock mode.
export USE_CHRONOS_API_MOCK='gui'
export CHRONOS_SHOW_PAINT_RECTS='no'
EOL

    cat >> ~/.pdbrc <<'EOL'
#Refresh the terminal - something disables keyboard echoing when running watch_guest.sh.
import os
os.system("stty sane")
EOL
fi

echo "Reloading environment. (Run . ~/.bashrc if this fails?)"
. ~/.bashrc

read -p "Optional: Show a cow on SSH login to help with identification? y/N " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setting up Cowsay."
    apt install cowsay --yes
    cat > /etc/profile.d/cow.sh <<'EOS'
/usr/games/cowsay << EOQ
You have reached Chronos camera #$(gdbus call --system --dest ca.krontech.chronos.control --object-path /ca/krontech/chronos/control --method ca.krontech.chronos.control.get "['cameraSerial']" | grep --only-matching --perl-regexp '(?<=<'\'').*(?='\''>)' -), model $(gdbus call --system --dest ca.krontech.chronos.control --object-path /ca/krontech/chronos/control --method ca.krontech.chronos.control.get "['cameraModel']" | grep --only-matching --perl-regexp '(?<=<'\'').*(?='\''>)' -).
For help and documentation, see http://forum.krontech.ca/ and https://github.com/krontech.
EOQ
EOS
else
    read -p "Well, how about a pony then? y/N " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Setting up Ponysay. You have good taste, my friend!" #And good patience, because this is slower than cowsay by a fair margin.
        wget http://www.vcheng.org/ponysay/ponysay_3.0.2-1_all.deb
        dpkg -i ponysay_3.0.2-1_all.deb
        rm ponysay_3.0.2-1_all.deb
        cat > /etc/profile.d/horse.sh <<'EOS'
ponysay ++pony aquarius ++pony archlinux ++pony aries ++pony artemis ++pony aurora ++pony barbara ++pony bubbleberry ++pony butterscotch ++pony buttonmom ++pony calamity ++pony cancer ++pony capricorn ++pony childrenofthenight ++pony chrome ++pony coffeetalk ++pony coffeewalk ++pony danger ++pony doctornohat ++pony donutpony ++pony drhooves1 ++pony drhooves10 ++pony drhooves11 ++pony drhooves8 ++pony drhooves9 ++pony drhoovesdiscorded ++pony drizzle ++pony duskshine ++pony elusive ++pony faust ++pony firefox ++pony fluffle ++pony freckles ++pony fyrefly ++pony fyreflyready ++pony gemini ++pony gleamingshield ++pony gnupony ++pony hestelle ++pony internetexplorer ++pony johndelancie ++pony jristz ++pony kingsley ++pony kingsleybanner ++pony leo ++pony libra ++pony littlepip ++pony maandree ++pony milky ++pony milkylay ++pony molestia ++pony nyx ++pony nyxdisguised ++pony opera ++pony orion ++pony oscura ++pony paradise ++pony pinkaminacupcake ++pony pisces ++pony pizzapony ++pony posey ++pony princeartemis ++pony rainbowblitz ++pony reddit ++pony robodash ++pony sagittarius ++pony scorpio ++pony seabreeze ++pony sealyra ++pony slanderpony ++pony snowdrop ++pony snowdrop-crew ++pony solaris ++pony sparkler ++pony starstruck ++pony surprise ++pony sweetiebot ++pony taurus ++pony tempo ++pony ticket ++pony twibrain ++pony virgo ++pony wiggles ++pony woona ++pony woonanohat << EOQ
You have reached Chronos camera #$(gdbus call --system --dest ca.krontech.chronos.control --object-path /ca/krontech/chronos/control --method ca.krontech.chronos.control.get "['cameraSerial']" | grep --only-matching --perl-regexp '(?<=<'\'').*(?='\''>)' -), model $(gdbus call --system --dest ca.krontech.chronos.control --object-path /ca/krontech/chronos/control --method ca.krontech.chronos.control.get "['cameraModel']" | grep --only-matching --perl-regexp '(?<=<'\'').*(?='\''>)' -).
For help and documentation, see http://forum.krontech.ca/ and https://github.com/krontech.
EOQ
EOS
    else
        echo "Skipped custom banner."
    fi
fi