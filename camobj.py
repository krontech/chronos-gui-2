
# Camera class
#from mem import fpga_mmio
import time
import pdb

from termcolor import colored
from mmapregisters import *
from memobj import MemObject
from sensorobj import SensorObject
from lux1310 import Lux1310Object
import fpgah
#import sys, smbus
#import pyi2cflash-0.1.1

#from smbus2 import SMBus

from smbus2 import SMBusWrapper
from smbus2 import SMBus

'''    
bus = SMBus()
bus.open(1)

v = bus.read_byte(80, 0)
print (f"EEPROM: {hex(v)}")
'''

from ioports import board_chronos14_ioports

MAX_FRAME_LENGTH = 0xf000
REC_START_ADDR = MAX_FRAME_LENGTH * 4

CAMERA_SERIAL_I2CADDR =	0x54
CAMERA_SERIAL_LENGTH =	32
CAMERA_SERIAL_OFFSET =	0



def i2c_eeprom_do_read(addr,  offset,  leng):
	bus = SMBus(1)
	#for i in range(1):
	#	b = bus.read_byte_data(CAMERA_SERIAL_I2CADDR + i, CAMERA_SERIAL_OFFSET)
	#	print(b)
	#bus.close()
	# print ("huh?")

	with SMBusWrapper(1) as bus:
		# Read a block of 16 bytes from address 80, offset 0
		# block = bus.read_i2c_block_data(addr, offset, leng)
		block = bus.read_i2c_block_data(84 , 30, leng)
		# Returned value is a list of 16 bytes
		print(block)



class CamObject:



	ioports = board_chronos14_ioports

		# self.CamInit()


	print ("continue")
	mem = MemObject()
	mem.CtypesTest()

	# exit()

	FPGAWrite32 = mem.FPGAWrite32
	FPGAWrite16 = mem.FPGAWrite16
	FPGAWrite8 = mem.FPGAWrite8

	#pdb.set_trace()
	sensor = Lux1310Object(mem)


	def __init__(self):
		print ("CamObject Init")
		self.CamInit()
		#thiscam = self
	
		
	#print("CamObject created")
	# mem = MemObject()



	'''
	int err;
	err = ioctl(fd, I2C_SLAVE, addr);
	if (err < 0) {
		return err;
	}

	err = i2c_eeprom_write_chunk(fd, addr, offset, NULL, 0, offsz);
	if (err < 0) {
		return err;
	}
	usleep(1000);
	err = read(fd, buf, len);
	return err;
	'''

	def image_sensor_bpp(self):
		return 12


	def i2c_eeprom_read16(fd, addr, offset, leng):
		return i2c_eeprom_do_read(fd, addr, offset, leng, 2);
		pass
		#print ("EEPROM")
		#print (pyi2cflash.read(addr, offset, leng))


	def ReadSerial():
		#iofile = ioports["eeprom-i2c"]
		#fd = open(iofile, O_RDWR)
		#return i2c_eeprom_read16(fd, CAMERA_SERIAL_I2CADDR, CAMERA_SERIAL_OFFSET, CAMERA_SERIAL_LENGTH);
		i2c_eeprom_do_read(CAMERA_SERIAL_I2CADDR, CAMERA_SERIAL_OFFSET, CAMERA_SERIAL_LENGTH)

	def TestLive(self):
		print("TESTING LIVE!!!!!")
		self.sensor.OpsDict["SetPeriod"](self.sensor, 1000000)
		self.sensor.OpsDict["SetExposure"](self.sensor, 100000)
		self.sensor.OpsDict["CalSuffix"]()
		self.sensor.OpsDict["SetGain"](self.sensor, 12)
		self.sensor.OpsDict["SetResolutions"](self.sensor)
		self.sensor.OpsDict["GetConstraints"](self.sensor)
		self.sensor.OpsDict["CalGain"]()
		print("END TESTING LIVE!!!!!")


		
		# self.CamInit()

	def SetLiveTiming(self, hOutRes, vOutRes, maxFPS):

		print("SETLIVETIMING!!")
		pxClock = 100000000
		hSync = 50
		hPorch = 166
		vSync = 3
		vPorch = 38

		hPeriod = hOutRes + hSync + hPorch + hSync

		# Calculate minimum hPeriod to fit within the max vertical
		# resolution and make sure hPeriod is equal to or larger
	 
		minHPeriod = (pxClock / ((self.sensor.vMaxRes + vPorch + vSync + vSync) * maxFPS)) + 1; # the +1 is just to round up
		if hPeriod < minHPeriod: 
			hPeriod = minHPeriod

		# calculate vPeriod and make sure it's large enough for the frame
		vPeriod = pxClock / (hPeriod * maxFPS)
		if vPeriod < (vOutRes + vSync + vPorch + vSync):
			vPeriod = vOutRes + vSync + vPorch + vSync
	
		# calculate FPS for debug output
		fps = pxClock / (vPeriod * hPeriod)
		print (f"FPS = {fps}")
		print ("Timing: %d*%d@%d (%d*%d max: %d)\n", \
			   (hPeriod - hSync - hPorch - hSync), (vPeriod - vSync - vPorch - vSync), \
			   fps, hOutRes, vOutRes, maxFPS)

		g = self.sensor.ImageGeometry
		self.mem.FPGAWrite32("DISPLAY_H_RES", g.hres)
		self.mem.FPGAWrite32("DISPLAY_V_RES", g.vres)
		print (f"ImageGeometry: {g}")


	def getFPGAVersion(self):
		ver = self.mem.FPGARead16("FPGA_VERSION")
		print (f"Version is {ver}")
		return ver

	def getFPGASubVersion(self):
		sver = self.mem.FPGARead16("FPGA_SUBVERSION")
		print (f"Subversion is {sver}")
		return sver

	def setLiveOutputTiming(self, hRes, vRes, hOutRes, vOutRes, maxFps):

		#consts:
		hSync = 1
		hBackPorch = 64
		hFrontPorch = 4
		vSync = 1
		vBackPorch = 4
		vFrontPorch = 1
	
		pxClock = 100000000
	
		# minHPeriod;
		# hPeriod;
		# vPeriod;
		# UInt32 fps;

		# FPGA revision 3.14 and higher use a 133MHz video clock. 
		if ((self.getFPGAVersion() > 3) or (self.getFPGASubVersion() >= 14)):
			print ("Faster FPGA clock enabled")
			pxClock = 133333333

		hPeriod = hSync + hBackPorch + hOutRes + hFrontPorch;

		# calculate minimum hPeriod to fit within the 1024 max vertical resolution
		# and make sure hPeriod is equal or larger
		minHPeriod = (pxClock // ((1024+vBackPorch+vSync+vFrontPorch) * maxFps)) + 1 # the +1 is just to round up
		if hPeriod < minHPeriod:
			hPeriod = minHPeriod

		# calculate vPeriod and make sure it's large enough for the frame
		vPeriod = pxClock // (hPeriod * maxFps)
		if (vPeriod < (vOutRes + vBackPorch + vSync + vFrontPorch)):
			vPeriod = (vOutRes + vBackPorch + vSync + vFrontPorch)
	
		# calculate FPS for debug output
		fps = pxClock // (vPeriod * hPeriod);
		print ("setLiveOutputTiming: %d*%d@%d (%d*%d max: %d)" % \
		   ((hPeriod - hBackPorch - hSync - hFrontPorch),
		   (vPeriod - vBackPorch - vSync - vFrontPorch),
		   fps, hOutRes, vOutRes, maxFps))

		self.mem.FPGAWrite16("DISPLAY_H_RES", hRes)
		self.mem.FPGAWrite16("DISPLAY_H_OUT_RES", hOutRes)
		self.mem.FPGAWrite16("DISPLAY_V_RES", vRes)
		self.mem.FPGAWrite16("DISPLAY_V_OUT_RES", vOutRes)

		self.mem.FPGAWrite16("DISPLAY_H_PERIOD", hPeriod - 1)
		self.mem.FPGAWrite16("DISPLAY_H_SYNC_LEN", hSync)
		self.mem.FPGAWrite16("DISPLAY_H_BACK_PORCH", hBackPorch)

		self.mem.FPGAWrite16("DISPLAY_V_PERIOD", vPeriod - 1)
		self.mem.FPGAWrite16("DISPLAY_V_SYNC_LEN", vSync)
		self.mem.FPGAWrite16("DISPLAY_V_BACK_PORCH", vBackPorch)


	def FakeIO(self):
		print ("TODO: don't do fake IO")
		self.mem.fpga_write16(0xa0, 0x1)
		self.mem.fpga_write16(0xa4, 0x1)
		self.mem.fpga_write16(0xa8, 0x0)
		self.mem.fpga_write32(0x60, 0x0)	
		self.mem.fpga_write16(0xb4, 0x0)
		self.mem.fpga_write16(0xb0, 0x0)
		self.mem.fpga_write16(0xac, 0x2)
		self.mem.fpga_write16(0xbc, 0x0)
		self.mem.fpga_write16(0xbc, 0x0)
		self.mem.fpga_write16(0xbc, 0x0)


	def Fake16(self, addr, data):
			# breakpoint()
			print (f"--- faking 16 bit (0x{(addr * 2):x}, (0x{data:x})")
			self.mem.fpga_write16(addr * 2, data)
	def Fake32(self, addr, data):
			# breakpoint()
			print (f"=== faking 32 bit (0x{(addr * 2):x}, (0x{data:x})")
			self.mem.fpga_write32(addr * 2, data)

	def FakeInit(self):
		print ("TODO: don't do fake init")

		self.Fake16(0x36, 0x52)
		self.Fake32(0x10, 0x12e5a)
		self.Fake16(0x24, 0xf000)
		self.Fake16(0x214, 0x500)
		self.Fake16(0x218, 0x500)
		self.Fake16(0x216, 0x400)
		self.Fake16(0x220, 0x400)
		self.Fake16(0x208, 0x652)
		self.Fake16(0x20c, 0x1)
		self.Fake16(0x210, 0x40)
		self.Fake16(0x20a, 0x405)
		self.Fake16(0x20e, 0x1)
		self.Fake16(0x212, 0x4)
		self.Fake32(0x30, 0x0)
		self.Fake16(0x5e, 0x0)
		self.Fake32(0x10, 0x78)
		self.Fake32(0x28, 0x1fffe000)
		self.Fake32(0x82, 0x0)
		self.Fake32(0x80, 0x200c)
		self.Fake16(0x24, 0xf000)
		self.Fake32(0x20, 0x2)
		self.Fake32(0x20, 0x0)
		self.Fake16(0x5e, 0x0)
		self.Fake32(0x10, 0x12e5a)
		self.Fake32(0x10, 0x0)
		self.Fake32(0x10, 0x12e5a)
		self.Fake16(0x278, 0x10e5)
		self.Fake16(0x27a, 0x10e5)
		self.Fake16(0x27c, 0x10e5)
		self.Fake16(0x260, 0x1ea2)
		self.Fake16(0x262, 0xf6c6)
		self.Fake16(0x264, 0xfc41)
		self.Fake16(0x268, 0xfb1d)
		self.Fake16(0x26a, 0x163b)
		self.Fake16(0x26c, 0xfe74)
		self.Fake16(0x26e, 0x209)
		self.Fake16(0x270, 0xf0c1)
		self.Fake16(0x272, 0x1a63)
		self.Fake16(0x278, 0x16ce)
		self.Fake16(0x27a, 0x10e5)
		self.Fake16(0x27c, 0x1ac3)
		self.Fake32(0x200, 0x280)
		self.Fake32(0x222, 0x19)
		self.Fake32(0x10, 0x12c31)





	 
	def CamInit(self):

		print("CamInit()")
		
	
		#breakpoint()	

		# Reset the FPGA
		#self.mem.fpga_write16(SYSTEM_RESET, 1)
		
		#TESTING! no reset
		#self.mem.FPGAWrite16("SYSTEM_RESET", 1)
		

		# Give it some time
		time.sleep(0.2)

		self.setLiveOutputTiming(1296, 1024, 1280, 1024, 60)

		print (f"pixel rate is {self.sensor.ImageSensor.pixel_rate}")
		 
		maxfps = self.sensor.ImageSensor.pixel_rate / \
			(self.sensor.ImageSensor.h_max_res * self.sensor.ImageSensor.v_max_res)
		print (f"maxfps is {maxfps}")
		
		g = self.sensor.ImageGeometry 
		g.hres = self.sensor.ImageSensor.h_max_res
		g.vres = self.sensor.ImageSensor.v_max_res
		g.hoffset = 0
		g.voffset = 0

		print (f"h_max_res = {self.sensor.ImageSensor.h_max_res}")

		#TODO: move this to somewhere better
		self.sensor.hMaxRes = self.sensor.ImageSensor.h_max_res
		self.sensor.vMaxRes = self.sensor.ImageSensor.v_max_res

		# print (self.sensor)
		# Configure the FIFO threshold and image sequencer


		self.mem.FPGAWrite16("SENSOR_FIFO_START_W_THRESH", 0x100)
		self.mem.FPGAWrite16("SENSOR_FIFO_STOP_W_THRESH", 0x100)



		self.mem.FPGAWrite32("SEQ_LIVE_ADDR_0", MAX_FRAME_LENGTH)
		self.mem.FPGAWrite32("SEQ_LIVE_ADDR_1", MAX_FRAME_LENGTH * 2)
		self.mem.FPGAWrite32("SEQ_LIVE_ADDR_2", MAX_FRAME_LENGTH * 3)
		self.mem.FPGAWrite32("SEQ_REC_REGION_START", REC_START_ADDR) #in camApp this uses setRecRegionStartWords

		print ("---------")
		#temporary single definition; move to fpgah.py
		DISPLAY_CTL_READOUT_INHIBIT = (1 << 3)

		dctrl = self.mem.fpga_read32(DISPLAY_CTL)
		print (f"dctrl is 0x{dctrl:x}")
		dctrl &= ~DISPLAY_CTL_READOUT_INHIBIT
		print (f"AND mask is 0x{DISPLAY_CTL_READOUT_INHIBIT:x}")
		#MANUAL KLUDGE!
		dctrl = 0x2f0
		# exit()

		self.mem.FPGAWrite32("DISPLAY_CTL", dctrl)  #(18)

		# exit()

		self.mem.FPGAWrite32("IMAGER_FRAME_PERIOD", 100 * 4000)		# 18
		self.mem.FPGAWrite32("IMAGER_INT_TIME", 100 * 3900)			# 19

		# exit()


		#TODO - dereference through SensorObj:
		breakpoint()
		self.sensor._writeDACVoltages()
		# exit()

		# breakpoint()

		print (self.sensor)
		time.sleep(0.01)
		self.sensor.lux1310SetReset(True)
		self.sensor.lux1310SetReset(False)
		time.sleep(0.001)

		print ("#############\nLux has been reset\n#############")

		# self.sensor.Lux1310RegDump()

		# breakpoint()

		#TODO: this goes into sensor abstraction
		self.sensor.Lux1310Write("LUX1310_SCI_SRESET_B", 0)

		# exit()

		self.sensor.SensorInit2()

		# exit()

		#self.sensor.Lux1310AutoPhaseCal()			

		self.sensor.LuxInit2()

		# exit()

		# breakpoint()

		self.FakeIO()

		# breakpoint()

		self.setImagerSettings()

		# exit()

		breakpoint()
		self.FakeInit()

		# frame_words = int(((self.sensor.hMaxRes * self.sensor.vMaxRes * self.image_sensor_bpp()) / 8 + (32 - 1)) / 32)
		# print(f"frame_words = {frame_words}")
		# print(f"hMaxRes = {self.sensor.hMaxRes}")
		# self.FPGAWrite32("SEQ_FRAME_SIZE", (frame_words + 0x3f) & ~0x3f)
		



		# this was from daemon:
		# self.SetLiveTiming(self.sensor.hMaxRes, self.sensor.vMaxRes, 60)
		# print ("--> SENSOR:")
		# print (self.sensor.ImageGeometry)

		#ReadSerial()

		#sensor = SensorObject(mem)
		#sensor = Lux1310Object(mem)
	
	
	def setImagerSettings(self):
		#TODO: all this
		# self.mem.FPGAWrite32("IMAGER_INT_TIME", 0)
		# self.mem.FPGAWrite16("SENSOR_LINE_PERIOD", 0)
		self.mem.FPGAWrite32("IMAGER_INT_TIME", 0)
		

		self.sensor.Lux1310SetResolutions()
		#breakpoint()
		#self.sensor.Lux1310SetFramePeriod(self.sensor.currentPeriod, self.sensor.currentHRes, self.sensor.currentVRes)

		#FAKE:
		self.sensor.mem.FPGAWrite32("IMAGER_FRAME_PERIOD", 0x1716f)


		self.sensor.Lux1310SetGain(self.sensor.gain)

		self.sensor.Lux1310UpdateWavetableSetting()



		self.sensor.Lux1310LoadColGainFromFile()


		#TODO: finish this section instead of faking it


		#Set the timing generator to handle the line period
		# self.FPGAWrite16("SENSOR_LINE_PERIOD", \
		# 	max((self.sensor.currentHRes / LUX1310_HRES_INCREMENT) + 2, (sensor.wavetableSize + 3)) - 1)
		# time.sleep(0.01)
		# print ("About to setSlaveExposure")

		# self.sensor.setSlaveExposure(settings.exposure)
		# self.sensor.seqOnOff(true);



'''
	imagerSettings.hRes = settings.hRes;
	imagerSettings.stride = settings.stride;
	imagerSettings.vRes = settings.vRes;
	imagerSettings.hOffset = settings.hOffset;
	imagerSettings.vOffset = settings.vOffset;
	imagerSettings.period = settings.period;
	imagerSettings.exposure = settings.exposure;
	imagerSettings.gain = settings.gain;
	imagerSettings.disableRingBuffer = settings.disableRingBuffer;
	imagerSettings.mode = settings.mode;
	imagerSettings.prerecordFrames = settings.prerecordFrames;
	imagerSettings.segmentLengthFrames = settings.segmentLengthFrames;
	imagerSettings.segments = settings.segments;

    //Zero trigger delay for Gated Burst
    if(settings.mode == RECORD_MODE_GATED_BURST)
	io->setTriggerDelayFrames(0, FLAG_TEMPORARY);

	imagerSettings.frameSizeWords = ROUND_UP_MULT((settings.stride * (settings.vRes+0) * 12 / 8 + (BYTES_PER_WORD - 1)) / BYTES_PER_WORD, FRAME_ALIGN_WORDS);	//Enough words to fit the frame, but make it even

    UInt32 maxRecRegionSize = getMaxRecordRegionSizeFrames(imagerSettings.hRes, imagerSettings.vRes);  //(ramSize - REC_REGION_START) / imagerSettings.frameSizeWords;

    if(settings.recRegionSizeFrames > maxRecRegionSize)
	imagerSettings.recRegionSizeFrames = maxRecRegionSize;
    else
	imagerSettings.recRegionSizeFrames = settings.recRegionSizeFrames;

    setFrameSizeWords(imagerSettings.frameSizeWords);

	qDebug() << "About to sensor->loadADCOffsetsFromFile";
	sensor->loadADCOffsetsFromFile();

	loadColGainFromFile();

	qDebug()	<< "\nSet imager settings:\nhRes" << imagerSettings.hRes
				<< "vRes" << imagerSettings.vRes
				<< "stride" << imagerSettings.stride
				<< "hOffset" << imagerSettings.hOffset
				<< "vOffset" << imagerSettings.vOffset
				<< "exposure" << imagerSettings.exposure
				<< "period" << imagerSettings.period
				<< "frameSizeWords" << imagerSettings.frameSizeWords
				<< "recRegionSizeFrames" << imagerSettings.recRegionSizeFrames;

	if (settings.temporary) {
		qDebug() << "--- settings --- temporary, not saving";
	}
	else {
		qDebug() << "--- settings --- saving";
	appSettings.setValue("camera/hRes",                 imagerSettings.hRes);
	appSettings.setValue("camera/vRes",                 imagerSettings.vRes);
	appSettings.setValue("camera/stride",               imagerSettings.stride);
	appSettings.setValue("camera/hOffset",              imagerSettings.hOffset);
	appSettings.setValue("camera/vOffset",              imagerSettings.vOffset);
	appSettings.setValue("camera/gain",                 imagerSettings.gain);
	appSettings.setValue("camera/period",               imagerSettings.period);
	appSettings.setValue("camera/exposure",             imagerSettings.exposure);
	appSettings.setValue("camera/recRegionSizeFrames",  imagerSettings.recRegionSizeFrames);
	appSettings.setValue("camera/disableRingBuffer",    imagerSettings.disableRingBuffer);
	appSettings.setValue("camera/mode",                 imagerSettings.mode);
	appSettings.setValue("camera/prerecordFrames",      imagerSettings.prerecordFrames);
	appSettings.setValue("camera/segmentLengthFrames",  imagerSettings.segmentLengthFrames);
	appSettings.setValue("camera/segments",             imagerSettings.segments);
	}
'''


		#TODO do this properly














	# self.SetLiveTiming()


