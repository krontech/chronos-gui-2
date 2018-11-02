
import time
from camobj import CamObject

print ("Live Video Testing")





# main part

cam = CamObject()


def nicehex(n):
	return "0x" + ("0000000" + hex(n)[2:])[-4:]
def nicehex4(n):
	return "0x" + ("0000000" + hex(n)[2:])[-8:]

print ("LIVE FPGA registers")

#print (cam)

for i in range(0, 10, 4):
	mm = cam.mem.fpga_mmio.read32(i)
	print (nicehex(i), " - ", nicehex4(mm))

print ("LIVE!")

print (cam.sensor.ImageGeometry.hres)
print (cam.sensor.numfunc())


sw = cam.GPIORead("encoder-sw")
print(f"Encoder switch is {sw}")

for x in range(40):
	cam.GPIOWrite("record-led.0", x & 1)
	cam.GPIOWrite("record-led.1", not (x & 1))
	time.sleep(0.05)

while True:
	sw = cam.GPIORead("encoder-sw")
	cam.GPIOWrite("record-led.0", sw)
	cam.GPIOWrite("record-led.1", not sw)




cam.TestLive()

# print (cam.sensor.ImageConstraints)
# print (cam.sensor.ImageGeometry)
print (cam.sensor.ImageSensor)
