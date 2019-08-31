#!/bin/bash

#Split cam-json call into two because it can't parse the whole thing at once.
#Note: combOr3 should be set to "While Record Button Held" in the triggers/io screen.
cam-json --control set - << EOF
{"ioMapping": {"combAnd": {"debounce": 0, "invert": 0, "source": "alwaysHigh"},
               "combOr1": {"debounce": 0, "invert": 0, "source": "io1"},
               "combOr2": {"debounce": 0, "invert": 0, "source": "io3"},
               "combOr3": {"debounce": 0, "invert": 0, "source": "none"},
               "combXOr": {"debounce": 0, "invert": 0, "source": "alwaysHigh"},
               "delay": {"debounce": 0, "delayTime": 0.0, "invert": 0, "source": "toggle"},
               "gate": {"debounce": 0, "invert": 0, "source": "none"},
               "io1": {"debounce": 0, "driveStrength": 0, "invert": 0, "source": "none"},
               "io1In": {"threshold": 4.998578}}}
EOF
cam-json --control set - << EOF
{"ioMapping": {"io2": {"debounce": 0, "driveStrength": 0, "invert": 0, "source": "none"},
               "io2In": {"threshold": 2.502708},
               "shutter": {"debounce": 0, "invert": 0, "shutterTriggersFrame": 0, "source": "none"},
               "start": {"debounce": 1, "invert": 0, "source": "comb"},
               "stop": {"debounce": 1, "invert": 1, "source": "delay"},
               "toggleClear": {"debounce": 0, "invert": 0, "source": "none"},
               "toggleFlip": {"debounce": 0, "invert": 0, "source": "comb"},
               "toggleSet": {"debounce": 0, "invert": 0, "source": "none"},
               "trigger": {"debounce": 0, "invert": 0, "source": "none"}}}
EOF
