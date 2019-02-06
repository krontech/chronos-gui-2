# -*- coding: future_fstrings -*-

#!/usr/bin/python
import numpy
import pychronos
import recSequencer
import datetime
from termcolor import cprint


columnOffsetMemory    = pychronos.fpgamap(0x5000, 0x1000)
columnGainMemory      = pychronos.fpgamap(0x1000, 0x1000)
columnLinearityMemory = pychronos.fpgamap(0xD000, 0x1000)
seq = recSequencer.recSequencer()
display = pychronos.display()
rawRegisters = pychronos.fpgamap(0x0000, 0x1000)


timerTime = -1

def doYield():
	print("YIELD!")

def timer(msg):
	return
	print (msg)


def doBlackCal(cam, useLiveBuffer=False):
	print("doBlackCal")
	# get the resolution from the display properties
	xres = display.hRes
	yres = display.vRes

	# for col in range(16):
	#     columnLinearityMemory[col] = 1
  
	
	#-----------------------------------------------------------------------
	if (useLiveBuffer):
		origAddress = [seq.liveAddr[0], seq.liveAddr[1], seq.liveAddr[2]]
		page = 0
		seq.liveAddr[0], seq.liveAddr[1], seq.liveAddr[2] = origAddress[page], origAddress[page], origAddress[page]
		while(rawRegisters.mem32[0x70//4] != origAddress[page]): pass
		page ^= 1
		img = numpy.asarray(pychronos.readframe(seq.liveAddr[page], xres, yres))
		for i in range(15):
			seq.liveAddr[0], seq.liveAddr[1], seq.liveAddr[2] = origAddress[page], origAddress[page], origAddress[page]
			while(rawRegisters.mem32[0x70//4] != origAddress[page]): pass
			page ^= 1
			img += pychronos.readframe(seq.liveAddr[page], xres, yres)
			doYield()
		seq.liveAddr[0], seq.liveAddr[1], seq.liveAddr[2] = origAddress[0], origAddress[1], origAddress[2]
	else:
		cam.mem.GPIOWrite("record-led.0", 1)
		cam.mem.GPIOWrite("record-led.1", 1)
		seq.recordCountFrames(16)
		cam.mem.GPIOWrite("record-led.0", 0)
		cam.mem.GPIOWrite("record-led.1", 0)
		img = numpy.asarray(pychronos.readframe(seq.regionStart, xres, yres))
		for i in range(15):
			img += pychronos.readframe(seq.regionStart + (seq.frameSize*i), xres, yres)
			doYield()

	timer("got frame")
	img /= 16
	#-----------------------------------------------------------------------
	timer("divide by 16")
	img = numpy.float32(img)
	timer("convert to float")
	gains = numpy.float32([0.0]*xres)
	linearity = numpy.float32([0.0]*xres)
	for i in range(xres):
		gains[i]     = columnGainMemory.mem16[i]
		linearityVal = columnLinearityMemory.mem16[i]
		if (linearityVal > 32767): linearityVal = -(65536-linearityVal)
		linearity[i] = linearityVal
	timer("calc gain and linearity")
	gains /= 4096
	linearity /= (2**21)
	# linearity /= (2**100)
	timer("normalize gain and linearity")
	print("gains:     ", gains[0:16])
	print("linearity: ", linearity[0:16])

	processed = (linearity * (img * img)) + (gains * img)
	doYield()
	timer("processing")
	columnOffset = numpy.int16(numpy.average(processed, axis=0))
	print("columnOffsets: ", columnOffset)
	timer("column offsets")
	processed = numpy.int16(processed)
	
	fpn = numpy.uint16((processed - columnOffset))
	print("fpn: ", fpn)
	pychronos.writeframe(0, fpn)
	timer("write FPN")

	columnOffset = numpy.uint16(numpy.int16(-columnOffset))

	for i in range(len(columnOffset)):
		columnOffsetMemory.mem16[i] = int(columnOffset[i])
	timer("write offsets")

if __name__ == '__main__':
	doBlackCal()
