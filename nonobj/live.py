

from camobj import *

print ("Live Video Testing")






def cam_init(cam):

	frame_words = 0
	maxfps = 3






# main part

cam = CamObject()


def nicehex(n):
	return "0x" + ("0000000" + hex(n)[2:])[-4:]
def nicehex4(n):
	return "0x" + ("0000000" + hex(n)[2:])[-8:]

print ("LIVE FPGA registers")

print (cam)
print (cam.fpga)

for i in range(0, 128, 4):
	mm = cam.fpga.read32(i)
	print (nicehex(i), " - ", nicehex4(mm))

print ("LIVE!")
