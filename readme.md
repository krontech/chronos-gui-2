## Camera User Interface

cam-ui is a Python3 replacement for the c++11-based camApp GUI. The original
camApp was designed as a monolith, and is being broken apart into two
pieces – an API and a GUI – which have clearer responsibilities.

### Project Overview
There are five major components to the Chronos project. From lowest level
to highest, we have:

- The FPGA driver, which is controlled by the camera API.
- The camera D-Bus API, which controls the FPGA driver and talks to the back-of-camera interface and the HTTP server over D-Bus.
- **The back of camera interface, which takes input from the operator and controls the camera through the D-Bus API.**
- The web server, which exposes an HTTP API for controlling the camera. The server uses the D-Bus API internally.
- The web app, which takes input from the operator and controls the camera through the HTTP API.

This repository contains the back of camera interface.

### Historical Context
Why did we decide to rewrite our firmware?

In early 2018, our initial implementation of the Chronos 1.4 camera software was starting to cause problems. It was—quite reasonably at the time—built as a monolith using Qt 4. This got the kickstarter products out the door. As the product was refined, and more people started working on the code, long-running FPGA projects began conflicting with long-running GUI projects. Refactoring the code became quite difficult, so it was decided to split the initial camera software (_[camApp](https://github.com/krontech/chronos-cam-app)_) in to two components. One would take care of the FPGA, and one would take care of the UI. They would talk over a [D-Bus API](https://www.freedesktop.org/wiki/Software/dbus).

In the summer of 2018, it became apparent that we would be switching operating systems from Arago Linux to Debian Linux. To enable wifi on the camera, a WIFI dongle can be plugged into the USB port. However, as Arago Linux seems to have ceased development in in 2013, none of the dongles available in 2018 have supported drivers. Running Debian, driver support is much better.  

Running Debian also means we can compile modern libraries for our use, which was effectively impossible under Arago. To this end, as we were [planning a redesign of the user interface](http://forum.krontech.ca/index.php?topic=135.0) anyway, we decided to take the opportunity to upgrade our GUI library to Qt 5 from Qt 4, and from C++ to Python. This repository contains the "vanilla" Qt 5 Python port. (A Qt Quick 5 Python port is also in the works. One will be chosen as the winner at some point, when we have more experience with both of them.)

### Design Considerations
- We have the UI .xml files available to us from the original app.
  - We will use those files to get us up and running.
  - However, the custom C++ widgets are not portable.
- The new UI needs to respond to updates from the web app.
- Performance and memory overhead budgets must be respected - the Chronos 1.4 has 1GB memory available to the CPU, which must be shared between the API, the back-of-camera interface, the web server, Debian itself, and Krontech's development tooling.

### Contributing
Before submitting a pull request, it's a good idea to tell us what you're up to on [the forums](http://forum.krontech.ca/). Communication is the key to effective contribution.

Have a supersonic day! 🙂
