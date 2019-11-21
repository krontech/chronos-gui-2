#!/bin/bash
#Run this script on your camera to ready it for gui2 development.
set -euxo pipefail #enable "safe mode"

#Some pre-installation set-up.
    #We'll run our own gui, not camApp, so stop it.
    #We use the util/watch-camera scripts for development so we can
    #debug things when they go wrong.
    systemctl disable chronos-gui.service
    systemctl stop chronos-gui.service

    #Also, don't display legal when ssh'ing in.
    touch ~/.hushlogin

# install deps
    #Note: apt's python3-numpy python3-termcolor python3-dbus and pip3's python-periphery smbus2 are probably not needed.
    apt update && apt-get upgrade --yes
    apt install ca-certificates cowsay vim rsync curl python3-pip python3-pyqt5 python3-pyqt5.qtsvg python3-dbus udisks2 fonts-roboto qrencode --yes
    #pip3 install --upgrade setuptools #required for smbus2
    pip3 install typing future-fstrings # python-periphery smbus2 #Required for gui2 and pychronos.
    pip3 install pdbpp watchdog #Optional deps. "pdbpp" provides improvements to pdb. "watchdog" provides watchmedo, used for automatic deployment with util/watch-camera.
  
# install the back-of-camera interface & dev environment
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


exit #TODO: Figure out how to prompt for segments. For now, just comment stuff out. :p
#Optional Bonus Content
    
    #ponysay, a cowsay replacement
    cd ~
    wget http://www.vcheng.org/ponysay/ponysay_3.0.2-1_all.deb
    dpkg -i ponysay_3.0.2-1_all.deb
    rm ponysay_3.0.2-1_all.deb
    cat > /etc/profile.d/horse.sh <<'EOS'
ponysay ++pony aquarius ++pony archlinux ++pony aries ++pony artemis ++pony aurora ++pony barbara ++pony bubbleberry ++pony butterscotch ++pony buttonmom ++pony calamity ++pony cancer ++pony capricorn ++pony childrenofthenight ++pony chrome ++pony coffeetalk ++pony coffeewalk ++pony danger ++pony doctornohat ++pony donutpony ++pony drhooves1 ++pony drhooves10 ++pony drhooves11 ++pony drhooves8 ++pony drhooves9 ++pony drhoovesdiscorded ++pony drizzle ++pony duskshine ++pony elusive ++pony faust ++pony firefox ++pony fluffle ++pony freckles ++pony fyrefly ++pony fyreflyready ++pony gemini ++pony gleamingshield ++pony gnupony ++pony hestelle ++pony internetexplorer ++pony johndelancie ++pony jristz ++pony kingsley ++pony kingsleybanner ++pony leo ++pony libra ++pony littlepip ++pony maandree ++pony milky ++pony milkylay ++pony molestia ++pony nyx ++pony nyxdisguised ++pony opera ++pony orion ++pony oscura ++pony paradise ++pony pinkaminacupcake ++pony pisces ++pony pizzapony ++pony posey ++pony princeartemis ++pony rainbowblitz ++pony reddit ++pony robodash ++pony sagittarius ++pony scorpio ++pony seabreeze ++pony sealyra ++pony slanderpony ++pony snowdrop ++pony snowdrop-crew ++pony solaris ++pony sparkler ++pony starstruck ++pony surprise ++pony sweetiebot ++pony taurus ++pony tempo ++pony ticket ++pony twibrain ++pony virgo ++pony wiggles ++pony woona ++pony woonanohat << EOQ
You have reached Chronos camera #$(gdbus call --system --dest ca.krontech.chronos.control --object-path /ca/krontech/chronos/control --method ca.krontech.chronos.control.get "['cameraSerial']" | grep --only-matching --perl-regexp '(?<=<'\'').*(?='\''>)' -), model $(gdbus call --system --dest ca.krontech.chronos.control --object-path /ca/krontech/chronos/control --method ca.krontech.chronos.control.get "['cameraModel']" | grep --only-matching --perl-regexp '(?<=<'\'').*(?='\''>)' -).
For help and documentation, see http://forum.krontech.ca/ and https://github.com/krontech.
EOQ
EOS
    
#Ponysay is slow. Use cowsay instead:
    #If present, edit /etc/profile.d/horse.sh to use /usr/games/cowsay instead
    #   of ponysay. Ponysay takes a *moment* to run. 😭
    
#Static IP
    #Edit the eth0 section in /etc/network/interfaces on the camera like:
    #   auto eth0
    #   iface eth0 inet static
    #           address 192.168.1.214
    #           netmask 255.255.255.0
    #           gateway 192.168.1.1
    #Where "214" is your static IP address choice.