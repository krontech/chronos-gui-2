#!/bin/bash
echo "Starting record sequence."

echo "all off"
cam-json --control set - > /dev/null << EOF
{"ioMapping": {"start": {"debounce": 0, "invert": 0, "source": "none"},
               "stop":  {"debounce": 0, "invert": 0, "source": "none"}}}
EOF

sleep 0.25
echo "start on"
cam-json --control set - > /dev/null << EOF
{"ioMapping": {"start": {"debounce": 0, "invert": 0, "source": "alwaysHigh"},
               "stop":  {"debounce": 0, "invert": 0, "source": "none"}}}
EOF

sleep 0.25
echo "all off"
cam-json --control set - > /dev/null << EOF
{"ioMapping": {"start": {"debounce": 0, "invert": 0, "source": "none"},
               "stop":  {"debounce": 0, "invert": 0, "source": "none"}}}
EOF

sleep 1.00
echo "stop on"
cam-json --control set - > /dev/null << EOF
{"ioMapping": {"start": {"debounce": 0, "invert": 0, "source": "none"},
               "stop":  {"debounce": 0, "invert": 0, "source": "alwaysHigh"}}}
EOF

sleep 0.25
echo "all off"
cam-json --control set - > /dev/null << EOF
{"ioMapping": {"start": {"debounce": 0, "invert": 0, "source": "none"},
               "stop":  {"debounce": 0, "invert": 0, "source": "none"}}}
EOF

echo "Finished record sequence."