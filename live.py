
# import pdb; pdb.set_trace()

print("\n\nLive Video Testing")

# breakpoint()

import time
from camobj import CamObject
from termcolor import colored
# import camobj

# breakpoint()

# exit()
# main part

globvar = 123

cam = CamObject()

# exit()

def nicehex(n):
	return "0x" + ("0000000" + hex(n)[2:])[-4:]


def nicehex4(n):
	return "0x" + ("0000000" + hex(n)[2:])[-8:]


print("LIVE FPGA registers")

# print (cam)

for i in range(0, 10, 4):
	mm = cam.mem.fpga_mmio.read32(i)
	print(nicehex(i), " - ", nicehex4(mm))

print("LIVE!")

# print (cam.sensor.ImageGeometry.hres)
# print (cam.sensor.numfunc())


sw = cam.mem.GPIORead("encoder-sw")
print(f"Encoder switch is {sw}")

print ("----")
for x in range(10):
	cam.mem.GPIOWrite("record-led.0", x & 1)
	print("-")
	cam.mem.GPIOWrite("record-led.1", not (x & 1))
	time.sleep(0.08)
	print(x)
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

# breakpoint()
# cam.sensor.Lux1310ShowTestPattern()

# cam.TestLive()

# print (cam.sensor.ImageConstraints)
# print (cam.sensor.ImageGeometry)
# print (cam.sensor.ImageSensor)
