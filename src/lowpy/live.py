# -*- coding: future_fstrings -*-
# import pdb; pdb.set_trace()

print("\n\nLive Video Testing")

# breakpoint()

import time
from camobj import CamObject
from termcolor import colored
# from blackCal0 import *

# import blackCal
# import camobj

# breakpoint()

# exit()
# main part


# exit()

def nicehex(n):
	return "0x" + ("0000000" + hex(n)[2:])[-4:]


def nicehex4(n):
	return "0x" + ("0000000" + hex(n)[2:])[-8:]


cam = CamObject()


print("LIVE!")



sw = cam.mem.GPIORead("encoder-sw")
# print(f"Encoder switch is {sw}")

print ("----")
# for x in range(10):
# 	cam.mem.GPIOWrite("record-led.0", x & 1)
# 	cam.mem.GPIOWrite("record-led.1", not (x & 1))
# 	time.sleep(0.08)
cam.mem.GPIOWrite("record-led.0", 0)
cam.mem.GPIOWrite("record-led.1", 0)

# exit()

while 0:
	a = cam.mem.GPIORead("encoder-a")
	b = cam.mem.GPIORead("encoder-b")
	# b = cam.GPIORead("encoder-sw")
	# a = not cam.GPIORead("shutter-sw")
	cam.mem.GPIOWrite("record-led.0", a)
	cam.mem.GPIOWrite("record-led.1", b)

# cam.sensor.Lux1310RegDump()
print("........")



# now test recording things

# cam.setRecSequencerModeNormal();
# cam.startRecording();
# cam.stopRecording();


# cam.doBlackCal()
# doBlackCal()
# cam.doBlackCal0()
# cam.old_doBlackCal()
cam.callBlackCal()

# breakpoint()
# cam.sensor.Lux1310ZeroFPNArea()

# breakpoint()
# cam.sensor.Lux1310ShowTestPattern()

# cam.TestLive()

# print (cam.sensor.ImageConstraints)
# print (cam.sensor.ImageGeometry)
# print (cam.sensor.ImageSensor)
