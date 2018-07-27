#!/usr/bin/python
import time

data=open("kron-mower-800x480.data", "rb")
fbdev=open("/dev/fb1", "wb")

while True:
        rgb=data.read(3)
        if rgb:
                rgba=rgb[2] + rgb[1] + rgb[0] + '\xff'
                fbdev.write(rgba)
        else:
                time.sleep(1)

