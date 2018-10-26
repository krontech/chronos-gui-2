

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





cam.TestLive()

# print (cam.sensor.ImageConstraints)
# print (cam.sensor.ImageGeometry)
print (cam.sensor.ImageSensor)
