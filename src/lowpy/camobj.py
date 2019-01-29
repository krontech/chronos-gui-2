# -*- coding: future_fstrings -*-
# Camera class
#from mem import fpga_mmio
import time
from datetime import datetime
import pdb

from blackCal0 import *


import numpy

from termcolor import colored
# from ppretty import ppretty

from mmapregisters import *
from memobj import MemObject
from sensorobj import SensorObject
from lux1310 import Lux1310Object
# import fpgah
#import sys, smbus
#import pyi2cflash-0.1.1

#from smbus2 import SMBus

from smbus2 import SMBusWrapper
from smbus2 import SMBus

# import blackCal

'''    
bus = SMBus()
bus.open(1)

v = bus.read_byte(80, 0)
print (f"EEPROM: {hex(v)}")
'''

from ioports import board_chronos14_ioports

# import errorcodes		
import pychronos

MAX_FRAME_LENGTH = 0xf000
REC_START_ADDR = MAX_FRAME_LENGTH * 4
REC_REGION_START = MAX_FRAME_LENGTH * 4


CAMERA_SERIAL_I2CADDR =		0x54
CAMERA_SERIAL_LENGTH =		32
CAMERA_SERIAL_OFFSET =		0

RECORD_MODE_NORMAL =		0
RECORD_MODE_SEGMENTED =		1
RECORD_MODE_GATED_BURST =	2
RECORD_MODE_FPN =			3

#error codes:

SUCCESS                                   =   0


CAMERA_SUCCESS                            =   0  # try to use SUCCESS instead 
CAMERA_THREAD_ERROR                       =   1
CAMERA_ALREADY_RECORDING                  =   2
CAMERA_NOT_RECORDING                      =   3
CAMERA_NO_RECORDING_PRESENT               =   4
CAMERA_IN_PLAYBACK_MODE                   =   5
CAMERA_ERROR_SENSOR                       =   6
CAMERA_INVALID_IMAGER_SETTINGS            =   7
CAMERA_FILE_NOT_FOUND                     =   8
CAMERA_FILE_ERROR                         =   9
CAMERA_ERROR_IO                           =  10
CAMERA_INVALID_SETTINGS                   =  11
CAMERA_FPN_CORRECTION_ERROR               =  12
CAMERA_CLIPPED_ERROR                      =  13
CAMERA_LOW_SIGNAL_ERROR                   =  14
CAMERA_RECORD_FRAME_ERROR                 =  15
CAMERA_ITERATION_LIMIT_EXCEEDED           =  16
CAMERA_GAIN_CORRECTION_ERROR              =  17
CAMERA_MEM_ERROR                          =  18
CAMERA_WRONG_FPGA_VERSION                 =  19
CAMERA_DEAD_PIXEL_RECORD_ERROR            =  20
CAMERA_DEAD_PIXEL_FAILED                  =  21


ECP5_ALREAY_OPEN                          = 101
ECP5_NOT_OPEN                             = 102
ECP5_GPIO_ERROR                           = 103
ECP5_SPI_OPEN_FAIL                        = 104
ECP5_IOCTL_FAIL                           = 105
ECP5_FILE_IO_ERROR                        = 106
ECP5_MEMORY_ERROR                         = 107
ECP5_WRONG_DEVICE_ID                      = 108
ECP5_DONE_NOT_ASSERTED                    = 109


GPMCERR_FOPEN                             = 201
GPMCERR_MAP                               = 202


IO_ERROR_OPEN                             = 301
IO_FILE_ERROR                             = 302


LUPA1300_SPI_OPEN_FAIL                    = 401
LUPA1300_NO_DATA_VALID_WINDOW             = 402
LUPA1300_INSUFFICIENT_DATA_VALID_WINDOW   = 403
LUX1310_FILE_ERROR                        = 404


SPI_NOT_OPEN                              = 501
SPI_ALREAY_OPEN                           = 502
SPI_OPEN_FAIL                             = 503
SPI_IOCTL_FAIL                            = 504


UI_FILE_ERROR                             = 601
UI_THREAD_ERROR                           = 602


VIDEO_NOT_RUNNING                         = 701
VIDEO_RESOLUTION_ERROR                    = 702
VIDEO_OMX_ERROR                           = 703
VIDEO_FILE_ERROR                          = 704
VIDEO_THREAD_ERROR                        = 705


RECORD_THREAD_ERROR                       = 801
RECORD_NOT_RUNNING                        = 802
RECORD_ALREADY_RUNNING                    = 803
RECORD_NO_DIRECTORY_SET                   = 804
RECORD_FILE_EXISTS                        = 805
RECORD_DIRECTORY_NOT_WRITABLE             = 806
RECORD_ERROR                              = 807
RECORD_INSUFFICIENT_SPACE                 = 808


SETTINGS_LOAD_ERROR                       = 901
SETTINGS_SAVE_ERROR                       = 902	





columnOffsetMemory    = pychronos.fpgamap(0x5000//2, 0x1000)
columnGainMemory      = pychronos.fpgamap(0x1000//2, 0x1000)
columnLinearityMemory = pychronos.fpgamap(0xD000//2, 0x1000)
seq = pychronos.sequencer()
display = pychronos.display()
rawRegisters = pychronos.fpgamap(0x0000, 0x1000)







class SeqPgmMem:
	termRecTrig = 0
	termRecMem = 0 
	termRecBlkEnd = 0
	termBlkFull = 0
	termBlkLow = 0
	termBlkHigh = 0
	termBlkFalling = 0
	termBlkRising = 0
	nextBlk = 0
	blkSize = 0
	

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

class imgSetObj():
	hRes = 0                # pixels
	vRes = 0                # pixels
	stride = 0              # Number of pixels per line (allows for dark pixels in the last column)
	hRes = 1280
	vRes = 1024
	hOffset = 0             # active area offset from left
	vOffset = 0             # Active area offset from top
	exposure = 79441            # 10ns increments
	period = 94575              # Frame period in 10ns increments
	gain = 0
	frameSizeWords = 61440  # Number of words a frame takes up
	recRegionSizeFrames = 8734 # Number of frames in the entire record region
	mode = 0 				# Recording mode
	segments = 0            # Number of segments in segmented mode
	segmentLengthFrames = 8734 # Length of segment in segmented mode
	prerecordFrames = 0     # Number of frames to record before each burst in Gated Burst mode
	disableRingBuffer = 0

class recordingDataObj:
	valid = False
	hasBeenSaved = False
	imgset = 0




class CamObject:

	recording = False
	playbackMode = False
	videoHasBeenReviewed = False

	ioports = board_chronos14_ioports

		# self.CamInit()

	imagerSettings = imgSetObj()
	recordingData = recordingDataObj()

	print ("continue")
	mem = MemObject()
	# mem.CtypesTest()
	mem.MemTest()

	# breakpoint()

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
		return i2c_eeprom_do_read(fd, addr, offset, leng, 2)
		pass
		#print ("EEPROM")
		#print (pyi2cflash.read(addr, offset, leng))


	def ReadSerial():
		#iofile = ioports["eeprom-i2c"]
		#fd = open(iofile, O_RDWR)
		#return i2c_eeprom_read16(fd, CAMERA_SERIAL_I2CADDR, CAMERA_SERIAL_OFFSET, CAMERA_SERIAL_LENGTH)
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
	 
		minHPeriod = (pxClock / ((self.sensor.vMaxRes + vPorch + vSync + vSync) * maxFPS)) + 1 # the +1 is just to round up
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

		hPeriod = hSync + hBackPorch + hOutRes + hFrontPorch

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
		fps = pxClock // (vPeriod * hPeriod)
		print ("setLiveOutputTiming: %d*%d@%d (%d*%d max: %d)" % \
		   ((hPeriod - hBackPorch - hSync - hFrontPorch),
		   (vPeriod - vBackPorch - vSync - vFrontPorch),
		   fps, hOutRes, vOutRes, maxFps))

		print (f"pxClock is 0x{pxClock:x}, hPeriod is 0x{hPeriod:x}, vPeriod is 0x{vPeriod:x}")

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
		self.mem.FPGAWrite16(0xa0, 0x1)
		self.mem.FPGAWrite16(0xa4, 0x1)
		self.mem.FPGAWrite16(0xa8, 0x0)
		self.mem.FPGAWrite32(0x60, 0x0)	
		self.mem.FPGAWrite16(0xb4, 0x0)
		self.mem.FPGAWrite16(0xb0, 0x0)
		self.mem.FPGAWrite16(0xac, 0x2)
		self.mem.FPGAWrite16(0xbc, 0x0)
		self.mem.FPGAWrite16(0xbc, 0x0)
		self.mem.FPGAWrite16(0xbc, 0x0)


	def Fake16(self, addr, data):
			# breakpoint()
			# print (f"--- faking 16 bit (0x{(addr * 2):x}, (0x{data:x})")
			self.mem.FPGAWrite16(addr * 2, data)
	def Fake16b(self, addr, data):
			# breakpoint()
			# print (f"--- faking 16 bit (0x{(addr * 2):x}, (0x{data:x})")
			self.mem.FPGAWrite16(addr, data)
	def Fake32(self, addr, data):
			# breakpoint()
			# print (f"=== faking 32 bit (0x{(addr * 2):x}, (0x{data:x})")
			self.mem.FPGAWrite32(addr * 2, data)

	def FakeInit(self):
		print ("TODO: don't do fake init")

		self.Fake16(0x36, 0x52)		# SENSOR_LINE_PERIOD
		self.Fake32(0x10, 0x12e5a)	# IMAGER_INT_TIME
		self.Fake16(0x24, 0xf000)	# SEQ_FRAME_SIZE
		
		self.Fake16(0x214, 0x500)	# DISPLAY_H_RES
		self.Fake16(0x218, 0x500)	# DISPLAY_H_OUT_RES
		self.Fake16(0x216, 0x400)	# DISPLAY_V_RES
		self.Fake16(0x220, 0x400)	# DISPLAY_V_OUT_RES
		# self.Fake16(0x208, 0x652)	# DISPLAY_H_PERIOD
		self.Fake16(0x20c, 0x1)		# DISPLAY_H_SYNC_LEN
		self.Fake16(0x210, 0x40)	# DISPLAY_H_BACK_PORCH
		self.Fake16(0x20a, 0x405)	# DISPLAY_V_PERIOD
		self.Fake16(0x20e, 0x1)		# DISPLAY_V_SYNC_LEN
		self.Fake16(0x212, 0x4)		# DISPLAY_V_BACK_PORCH
		
		self.Fake32(0x30, 0x0)		# SEQ_TRIG_DELAY
		self.Fake16(0x5e, 0x0)		# EXT_SHUTTER_CTL
		self.Fake32(0x10, 0x78)		# IMAGER_INT_TIME
		self.Fake32(0x28, 0x1fffe000)	# SEQ_REGION_END
		self.Fake32(0x82, 0x0)		# ????
		self.Fake32(0x80, 0x200c)	# SEQ_PGM_MEM_START
		self.Fake16(0x24, 0xf000)	# SEQ_FRAME_SIZE
		self.Fake32(0x20, 0x2)		# SEQ_CTL
		self.Fake32(0x20, 0x0)		# SEQ_CTL
		self.Fake16(0x5e, 0x0)		# EXT_SHUTTER_CTL
		self.Fake32(0x10, 0x12e5a)	# IMAGER_INT_TIME
		self.Fake32(0x10, 0x0)		# IMAGER_INT_TIME
		self.Fake32(0x10, 0x12e5a)	# IMAGER_INT_TIME
		self.Fake16(0x278, 0x10e5)	# WL_DYNDLY_2
		self.Fake16(0x27a, 0x10e5)	# WL_DYNDLY_3
		self.Fake16(0x27c, 0x10e5)	# ???
		self.Fake16(0x260, 0x1ea2)	# \
		self.Fake16(0x262, 0xf6c6)	# |
		self.Fake16(0x264, 0xfc41)	# |
		self.Fake16(0x268, 0xfb1d)	# |
		self.Fake16(0x26a, 0x163b)	# |
		self.Fake16(0x26c, 0xfe74)	# CCM
		self.Fake16(0x26e, 0x209)	# |
		self.Fake16(0x270, 0xf0c1)	# |
		self.Fake16(0x272, 0x1a63)	# /
		self.Fake16(0x278, 0x16ce)	# WL_DYNDLY_2
		self.Fake16(0x27a, 0x10e5)	# WL_DYNDLY_3
		self.Fake16(0x27c, 0x1ac3)	# ???
		self.Fake32(0x200, 0x280)	# DISPLAY_CTL
		self.Fake32(0x222, 0x19)	# DISPLAY_PEAKING_THRESH
		self.Fake32(0x10, 0x12c31)	# IMAGER_INT_TIME

	#latest fakery:
		self.Fake16b(0x20, 0x15b9)	# 
		self.Fake16b(0x4f0, 0x10cc)	# 
		self.Fake16b(0x4f4, 0x10cc)	# 
		self.Fake16b(0x4f8, 0x10cc)	# 
		
		self.Fake16b(0x4c0, 0x1ea2)	# CCM
		self.Fake16b(0x4c4, 0xf6c6)	# CCM
		self.Fake16b(0x4c8, 0xfc41)	# CCM
		self.Fake16b(0x4d0, 0xfb1d)	# CCM
		self.Fake16b(0x4d4, 0x163b)	# CCM
		self.Fake16b(0x4d8, 0xfe74)	# CCM
		self.Fake16b(0x4dc, 0x209)	# CCM
		self.Fake16b(0x4e0, 0xf0c1)	# CCM_
		self.Fake16b(0x4e4, 0x1a63)	# CCM_
		self.Fake16b(0x4f0, 0x16ae)	# WL_DYNDLY_
		self.Fake16b(0x4f4, 0x10cc)	# WL_DYNDLY_3
		self.Fake16b(0x4f8, 0x1a9c)	# ???
		self.Fake16b(0x400, 0x290)	# DISPLAY_CTL
		self.Fake16b(0x444, 0x19)	# DISPLAY_PEAKING_THRESH
		self.Fake16b(0x20, 0x15b9)	# IMAGER_INT_TIME







	 
	def CamInit(self):

		print("CamInit()")
		
	
		#breakpoint()	

		# Reset the FPGA
		#self.mem.fpga_write16(SYSTEM_RESET, 1)
		
		#TESTING! no reset
		# self.mem.FPGAWrite16("SYSTEM_RESET", 1)
		

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
		# breakpoint()
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

			# breakpoint()
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


		# self.sensor.Lux1310SetGain(self.sensor.gain)

		self.sensor.Lux1310UpdateWavetableSetting()


		# breakpoint()
		self.sensor.Lux1310LoadColGainFromFile()

	def testor(self):
		pass


# Sequencer stuff

	def startRecording(self):
		if self.recording:
			return CAMERA_ALREADY_RECORDING
		if self.playbackMode:
			return CAMERA_IN_PLAYBACK_MODE

		print ("startRecording")
		print (f"mode is {self.imagerSettings.mode}")
		if self.imagerSettings.mode == RECORD_MODE_NORMAL:
			self.setRecSequencerModeNormal()

		elif self.imagerSettings.mode == RECORD_MODE_SEGMENTED:
			self.setRecSequencerModeNormal()

		elif self.imagerSettings.mode == RECORD_MODE_GATED_BURST:
			self.setRecSequencerModeGatedBurst(self.imagerSettings.prerecordFrames)

		elif self.imagerSettings.mode == RECORD_MODE_FPN:
			#this part is uncommented in the camApp code
			print ("RECORD_MODE_FPN")
			# self.setRecSequencerModeSingleBlock(16, 0) 
			pass


		self.recordingData.valid = False
		self.recordingData.hasBeenSaved = False
		# vinst->flushRegions()
		self.startSequencer()
		self.mem.GPIOWrite("record-led.0", 1)
		self.mem.GPIOWrite("record-led.1", 1)
		self.recording = True
		self.videoHasBeenReviewed = False

		# while (True):
		# 	print(self.recording)



		return SUCCESS
		

	def setRecSequencerModeNormal(self):

		seqPgm = SeqPgmMem

		if self.recording:
			return CAMERA_ALREADY_RECORDING
		if self.playbackMode:
			return CAMERA_IN_PLAYBACK_MODE

		# Set to one plus the last valid address in the record region
		self.setRecRegionEndWords(REC_REGION_START + self.imagerSettings.recRegionSizeFrames * self.imagerSettings.frameSizeWords)

		seqPgm.termRecTrig = 0
		seqPgm.termRecMem = 1 if self.imagerSettings.disableRingBuffer else 0     # This currently doesn't work, bug in record sequencer hardware
		seqPgm.termRecBlkEnd = 0 if ((RECORD_MODE_SEGMENTED == self.imagerSettings.mode) and (self.imagerSettings.segments > 1)) else 1
		seqPgm.termBlkFull = 0
		seqPgm.termBlkLow = 0
		seqPgm.termBlkHigh = 0
		seqPgm.termBlkFalling = 0
		seqPgm.termBlkRising = 1
		seqPgm.nextBlk = 0
		seqPgm.blkSize = (self.imagerSettings.recRegionSizeFrames if (self.imagerSettings.mode == RECORD_MODE_NORMAL) \
			else self.imagerSettings.recRegionSizeFrames // self.imagerSettings.segments) - 1 # Set to number of frames desired minus one
		
		smode = "normal" if self.imagerSettings.mode == RECORD_MODE_NORMAL else "segmented"
		print (f"Setting record sequencer mode to {smode}, disableRingBuffer = {self.imagerSettings.disableRingBuffer}, end = '')")
		print (f", segments = {self.imagerSettings.segments}, blkSize = {seqPgm.blkSize}")
		self.writeSeqPgmMem(seqPgm, 0)

		self.setFrameSizeWords(self.imagerSettings.frameSizeWords)

		return SUCCESS

	def setRecSequencerModeGatedBurst(self, prerecord):

		seqPgm = SeqPgmMem

		if self.recording:
			return CAMERA_ALREADY_RECORDING
		if self.playbackMode:
			return CAMERA_IN_PLAYBACK_MODE

		# Set to one plus the last valid address in the record region
		self.setRecRegionEndWords(REC_REGION_START + self.imagerSettings.recRegionSizeFrames * self.imagerSettings.frameSizeWords)
		
		# Two instruction program
		# Instruction 0 records to a single frame while trigger is inactive
		# Instruction 1 records as normal while trigger is active

		# When trigger is inactive, we sit in this 1-frame block, continuously overwriting that frame
		seqPgm.termRecTrig = 0
		seqPgm.termRecMem = 0
		seqPgm.termRecBlkEnd = 0
		seqPgm.termBlkFull = 0
		seqPgm.termBlkLow = 0
		seqPgm.termBlkHigh = 1	# Terminate when trigger becomes active
		seqPgm.termBlkFalling = 0
		seqPgm.termBlkRising = 1
		seqPgm.nextBlk = 1					# Go to next block when this one terminates
		seqPgm.blkSize = prerecord - 1		# Set to number of frames desired minus one

		self.writeSeqPgmMem(seqPgm, 0)

		seqPgm.termRecTrig = 0
		seqPgm.termRecMem = 1 if self.imagerSettings.disableRingBuffer else 0
		seqPgm.termRecBlkEnd = 0
		seqPgm.termBlkFull = 0
		seqPgm.termBlkLow = 1   # Terminate when trigger becomes inactive
		seqPgm.termBlkHigh = 0
		seqPgm.termBlkFalling = 0
		seqPgm.termBlkRising = 1
		seqPgm.nextBlk = 0		# Go back to block 0
		seqPgm.blkSize = self.imagerSettings.recRegionSizeFrames - 3		# Set to number of frames desired minus one BUG? minus three?

		print (f"---- Sequencer ---- Set to Gated burst mode, second block size: {seqPgm.blkSize+1}")

		self.writeSeqPgmMem(seqPgm, 0)

		self.setFrameSizeWords(self.imagerSettings.frameSizeWords)

		return SUCCESS


	def setRecSequencerModeSingleBlock(self, blockLength, frameOffset):
		seqPgm = SeqPgmMem

		if self.recording:
			return CAMERA_ALREADY_RECORDING
		if self.playbackMode:
			return CAMERA_IN_PLAYBACK_MODE

		# Set to one plus the last valid address in the record region
		self.setRecRegionEndWords(REC_REGION_START + (self.imagerSettings.recRegionSizeFrames+frameOffset) * self.imagerSettings.frameSizeWords)

		seqPgm.termRecTrig = 0
		seqPgm.termRecMem = 0
		seqPgm.termRecBlkEnd = 1
		seqPgm.termBlkFull = 1
		seqPgm.termBlkLow = 0
		seqPgm.termBlkHigh = 0	# Terminate when trigger becomes active
		seqPgm.termBlkFalling = 0
		seqPgm.termBlkRising = 0
		seqPgm.nextBlk = 0				# Go to next block when this one terminates
		seqPgm.blkSize = blockLength - 1		# Set to number of frames desired minus one

		# breakpoint()
		self.writeSeqPgmMem(seqPgm, 0)

		self.setFrameSizeWords(self.imagerSettings.frameSizeWords)

		return SUCCESS


	def stopRecording(self):
		if (not self.recording):
			return CAMERA_NOT_RECORDING
		self.terminateRecord()

		self.recordingData.valid = False
		self.recordingData.hasBeenSaved = False
		# vinst->flushRegions()
		self.mem.GPIOWrite("record-led.0", 0)
		self.mem.GPIOWrite("record-led.1", 0)
		# self.recording = True
		# self.videoHasBeenReviewed = False

		print (f"stopRecording: recording is {self.recording}")

		return SUCCESS


# Find the earliest fully valid block

	def endOfRec():
		print ("EndOfRec")

		print (f"--- Sequencer --- Total record region size: {self.imagerSettings.recRegionSizeFrames}")

		 # TODO: Need to check with the video pipeline if there were actually frames captured, but there is
		 # a possible race condition since both the UI and the pipeline are just polling the sequencer.
		
		 # For now, just assume that we always captured something.

		# this was commented out in camApp    
		# if(0 == recDataLength)
		# {
		# 	recordingData.valid = false;
		# 	recordingData.hasBeenSaved = true;		//We didn't record anything so there's nothing to lose by overwriting
		# }

		self.recordingData.imgset = self.imagerSettings
		self.recordingData.valid = true
		self.recordingData.hasBeenSaved = false
		self.mem.GPIOWrite("record-led.0", 0)
		self.mem.GPIOWrite("record-led.1", 0)
		self.recording = false



	def writeSeqPgmMem(self, seqPgm, address):
		# breakpoint()
		print ("WSPM")
		# print (ppretty(seqPgm))
		datalow = seqPgm.termRecTrig
		datalow += seqPgm.termRecMem << 1
		datalow += seqPgm.termRecBlkEnd << 2
		datalow += seqPgm.termBlkFull << 3
		datalow += seqPgm.termBlkLow << 4
		datalow += seqPgm.termBlkHigh << 5
		datalow += seqPgm.termBlkFalling << 6
		datalow += seqPgm.termBlkRising << 7
		datalow += seqPgm.nextBlk << 8   # 4 bit field
		datalow += (seqPgm.blkSize & 0xfffff) << 12  # 4 bit field here

		print (f"blkSize = {seqPgm.blkSize}")
		datahigh = seqPgm.blkSize >> 20	# the other 28 bits go here

		print (f"datahigh = {datahigh}, datalow = {datalow}")
		self.mem.FPGAWrite32((SEQ_PGM_MEM_START + address * 16) + 4, datahigh)
		self.mem.FPGAWrite32((SEQ_PGM_MEM_START + address * 16), datalow)

	def setFrameSizeWords(self, frameSize):
		self.mem.FPGAWrite32("SEQ_FRAME_SIZE", frameSize)


	def getRecording(self):
		return self.mem.FPGARead32("SEQ_STATUS") and SEQ_STATUS_RECORDING_MASK


	def startSequencer(self):
		reg = self.mem.FPGARead32("SEQ_CTL")
		self.mem.FPGAWrite32("SEQ_CTL", reg or SEQ_CTL_START_REC_MASK)
		self.mem.FPGAWrite32("SEQ_CTL", reg and (0xffffffff - SEQ_CTL_START_REC_MASK))


	def terminateRecord(self):
		reg = self.mem.FPGARead32("SEQ_CTL")
		self.mem.FPGAWrite32("SEQ_CTL", reg or SEQ_CTL_STOP_REC_MASK)
		self.mem.FPGAWrite32("SEQ_CTL", reg and (0xffffffff - SEQ_CTL_STOP_REC_MASK))

	def setRecRegionStartWords(self, start):
		self.mem.FPGAWrite32("SEQ_REC_REGION_START", start)


	def setRecRegionEndWords(self, end):
		self.mem.FPGAWrite32("SEQ_REC_REGION_END", end)

















		#TODO: finish this section instead of faking it


		#Set the timing generator to handle the line period
		# self.FPGAWrite16("SENSOR_LINE_PERIOD", \
		# 	max((self.sensor.currentHRes / LUX1310_HRES_INCREMENT) + 2, (sensor.wavetableSize + 3)) - 1)
		# time.sleep(0.01)
		# print ("About to setSlaveExposure")

		# self.sensor.setSlaveExposure(settings.exposure)
		# self.sensor.seqOnOff(true)








	def setSettings(self):



		self.imagerSettings.hRes = settings.hRes
		self.imagerSettings.stride = settings.stride
		self.imagerSettings.vRes = settings.vRes
		self.imagerSettings.hOffset = settings.hOffset
		self.imagerSettings.vOffset = settings.vOffset
		self.imagerSettings.period = settings.period
		self.imagerSettings.exposure = settings.exposure
		self.imagerSettings.gain = settings.gain
		self.imagerSettings.disableRingBuffer = settings.disableRingBuffer
		self.imagerSettings.mode = settings.mode
		self.imagerSettings.prerecordFrames = settings.prerecordFrames
		self.imagerSettings.segmentLengthFrames = settings.segmentLengthFrames
		self.imagerSettings.segments = settings.segments

		return





	def doBlackCalSequenced(self):

		# print (f"doBlackCal({xres}, {yres})")

		#this part is from startRecording()
		self.setRecSequencerModeSingleBlock(16, 0)
		self.recordingData.valid = False
		self.recordingData.hasBeenSaved = False
		# vinst->flushRegions()
		self.startSequencer()
		self.mem.GPIOWrite("record-led.0", 1)
		self.mem.GPIOWrite("record-led.1", 1)
		self.recording = True
		self.videoHasBeenReviewed = False

		self.doBlackCal(f)

		self.stopRecording()


	def recordFrames(self, numframes):
		print (f"Starting record of {numframes} frames")

		self.stopRecording()


		oldMode = self.imagerSettings.mode
		self.imagerSettings.mode = RECORD_MODE_FPN

		rec  = self.mem.FPGARead32("SEQ_STATUS") and SEQ_STATUS_RECORDING_MASK
		print (f"rec is {rec}")


		retVal = self.setRecSequencerModeSingleBlock(numframes + 1, 0)
		if SUCCESS != retVal:
			return retVal

		rec  = self.mem.FPGARead32("SEQ_STATUS") and SEQ_STATUS_RECORDING_MASK
		print (f"rec is {rec}")


		retVal = self.startRecording()
		if SUCCESS != retVal:
			return retVal

		rec  = self.mem.FPGARead32("SEQ_STATUS") and SEQ_STATUS_RECORDING_MASK
		print (f"rec is {rec}")


		usStart = datetime.now().microsecond
		print (f"now is {usStart} us")
		looping = True
		while looping:
			rec  = self.mem.FPGARead32("SEQ_STATUS") and SEQ_STATUS_RECORDING_MASK
			print (rec)
			time.sleep(0.001)
			looping = rec
		
		dsEnd = datetime.now().microsecond
		print (f"now is {dsEnd} us")

		elapsed = dsEnd - usStart
		if elapsed < 0:
			elapsed += 1000000

		print (f"elapsed time = {elapsed} us")			
			
		retVal = self.stopRecording()			


		if False:	#If after the timeout recording hasn't finished
			print("Error: Record failed to stop within timeout period.")

			retVal = self.stopRecording()
			if SUCCESS != retVal:
				print("Error: Stop Record failed")
			return CAMERA_RECORD_FRAME_ERROR

		print("Record done")

		self.imagerSettings.mode = oldMode
		return SUCCESS
	


	def doBlackCal(self, useLiveBuffer=False):

		
		# get the resolution from the display properties
		xres = display.hRes
		yres = display.vRes
		
		#-----------------------------------------------------------------------
		# this needs to be switched to using the record sequencer
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
		else:
			# record 16 frames
			# read out the first one (make the numpy object)
			# loop through the other 15 and add them to the buffer
			self.recordFrames(16)		

			#first frame
			img = numpy.asarray(pychronos.readframe(seq.regionStart, xres, yres))

			for i in range(15):
				img += pychronos.readframe(seq.regionStart + i * seq.frameSize, xres, yres)





			pass
		img /= 16

		#-----------------------------------------------------------------------

		img = numpy.float64(img)
		
		gains = numpy.float64([0.0]*xres)
		linearity = numpy.float64([0.0]*xres)
		for i in range(xres):
			gains[i]     = columnGainMemory.mem16[i]
			linearityVal = columnLinearityMemory.mem16[i]
			if (linearityVal > 32767): linearityVal = -(65536-linearityVal)
			linearity[i] = linearityVal
		gains /= 4096
		linearity /= (2**21)
		print("gains:     ", gains[0:16])
		print("linearity: ", linearity[0:16])

		processed = (linearity * (img * img)) + (gains * img)
		
		columnOffset = numpy.average(processed, axis=0)
		print("columnOffsets: ", columnOffset)

		fpn = numpy.uint16(numpy.int16((processed - columnOffset)))
		print("fpn: ", fpn)
		pychronos.writeframe(0, fpn)

		columnOffset = numpy.uint16(numpy.int16(-columnOffset))

		for i in range(len(columnOffset)):
			columnOffsetMemory.mem16[i] = int(columnOffset[i])



	def callBlackCal(self):
		self.doBlackCal()


	def old_doBlackCal(self, xres=1280, yres=1024):


		print (f"doBlackCal({xres}, {yres})")

		#this part is from startRecording()
		self.setRecSequencerModeSingleBlock(16, 0)
		self.recordingData.valid = False
		self.recordingData.hasBeenSaved = False
		# vinst->flushRegions()
		self.startSequencer()
		self.mem.GPIOWrite("record-led.0", 1)
		self.mem.GPIOWrite("record-led.1", 1)
		self.recording = True
		self.videoHasBeenReviewed = False



		#-----------------------------------------------------------------------
		# this needs to be switched to using the record sequencer
		img = numpy.asarray(pychronos.readframe(seq.liveAddr[0], 1280, 1024))
		for i in range(15):
			# time.sleep(0.1)
			# print (".")
			img += pychronos.readframe(seq.liveAddr[0], 1280, 1024)
		img /= 16
		#-----------------------------------------------------------------------

		img = numpy.float32(img)
		
		gains = numpy.float32([0.0]*xres)
		linearity = numpy.float64([0.0]*xres)
		for i in range(xres):
			gains[i]     = columnGainMemory.mem16[i]
			linearityVal = columnLinearityMemory.mem16[i]
			if (linearityVal > 32767): linearityVal = -(65536-linearityVal)
			linearity[i] = linearityVal
		gains /= 4096
		linearity /= (2**21)
		print("gains:     ", gains[0:16])
		print("linearity: ", linearity[0:16])

		processed = (linearity * (img * img)) + (gains * img)
		
		columnOffset = numpy.average(processed, axis=0)
		print("columnOffsets: ", columnOffset)

		fpn = numpy.uint16(numpy.int16(processed + columnOffset))
		print(" fpn: ", fpn)
		pychronos.writeframe(0, fpn)

		columnOffset = numpy.uint16(numpy.int16(columnOffset))

		for i in range(len(columnOffset)):
			columnOffsetMemory.mem16[i] = int(columnOffset[i])


		self.stopRecording()



	def doBlackCal0(self, xres=1280, yres=1024):
		print ("doBlackCal0")
		#-----------------------------------------------------------------------
		# this needs to be switched to using the record sequencer
		img = numpy.asarray(pychronos.readframe(seq.liveAddr[0], 1280, 1024))
		for i in range(15):
			# time.sleep(0.1)
			# print (".")
			img += pychronos.readframe(seq.liveAddr[0], 1280, 1024)
		img /= 16
		#-----------------------------------------------------------------------

		img = numpy.float32(img)
		
		gains = numpy.float32([0.0]*xres)
		linearity = numpy.float64([0.0]*xres)
		for i in range(xres):
			gains[i]     = columnGainMemory.mem16[i]
			linearityVal = columnLinearityMemory.mem16[i]
			if (linearityVal > 32767): linearityVal = -(65536-linearityVal)
			linearity[i] = linearityVal
		gains /= 4096
		linearity /= (2**21)
		print("gains:     ", gains[0:16])
		print("linearity: ", linearity[0:16])

		processed = (linearity * (img * img)) + (gains * img)
		
		columnOffset = numpy.average(processed, axis=0)
		print("columnOffsets: ", columnOffset)

		fpn = numpy.uint16(numpy.int16(processed + columnOffset))
		print(" fpn: ", fpn)
		pychronos.writeframe(0, fpn)

		columnOffset = numpy.uint16(numpy.int16(columnOffset))

		for i in range(len(columnOffset)):
			columnOffsetMemory.mem16[i] = int(columnOffset[i])





		'''

		# Zero trigger delay for Gated Burst
		if(settings.mode == RECORD_MODE_GATED_BURST)
		io->setTriggerDelayFrames(0, FLAG_TEMPORARY);

		self.imagerSettings.frameSizeWords = ROUND_UP_MULT((settings.stride * (settings.vRes+0) * 12 / 8 + (BYTES_PER_WORD - 1)) / BYTES_PER_WORD, FRAME_ALIGN_WORDS);	//Enough words to fit the frame, but make it even

		UInt32 maxRecRegionSize = getMaxRecordRegionSizeFrames(self.imagerSettings.hRes, self.imagerSettings.vRes);  //(ramSize - REC_REGION_START) / self.imagerSettings.frameSizeWords;

		if(settings.recRegionSizeFrames > maxRecRegionSize)
		self.imagerSettings.recRegionSizeFrames = maxRecRegionSize;
		else
		self.imagerSettings.recRegionSizeFrames = settings.recRegionSizeFrames;

		setFrameSizeWords(self.imagerSettings.frameSizeWords);

		qDebug() << "About to sensor->loadADCOffsetsFromFile";
		sensor->loadADCOffsetsFromFile();

		loadColGainFromFile();

		qDebug()	<< "\nSet imager settings:\nhRes" << self.imagerSettings.hRes
					<< "vRes" << self.imagerSettings.vRes
					<< "stride" << self.imagerSettings.stride
					<< "hOffset" << self.imagerSettings.hOffset
					<< "vOffset" << self.imagerSettings.vOffset
					<< "exposure" << self.imagerSettings.exposure
					<< "period" << self.imagerSettings.period
					<< "frameSizeWords" << self.imagerSettings.frameSizeWords
					<< "recRegionSizeFrames" << self.imagerSettings.recRegionSizeFrames;

	if (settings.temporary) {
		qDebug() << "--- settings --- temporary, not saving";
	}
	else {
		qDebug() << "--- settings --- saving";
	appSettings.setValue("camera/hRes",                 self.imagerSettings.hRes);
	appSettings.setValue("camera/vRes",                 self.imagerSettings.vRes);
	appSettings.setValue("camera/stride",               self.imagerSettings.stride);
	appSettings.setValue("camera/hOffset",              self.imagerSettings.hOffset);
	appSettings.setValue("camera/vOffset",              self.imagerSettings.vOffset);
	appSettings.setValue("camera/gain",                 self.imagerSettings.gain);
	appSettings.setValue("camera/period",               self.imagerSettings.period);
	appSettings.setValue("camera/exposure",             self.imagerSettings.exposure);
	appSettings.setValue("camera/recRegionSizeFrames",  self.imagerSettings.recRegionSizeFrames);
	appSettings.setValue("camera/disableRingBuffer",    self.imagerSettings.disableRingBuffer);
	appSettings.setValue("camera/mode",                 self.imagerSettings.mode);
	appSettings.setValue("camera/prerecordFrames",      self.imagerSettings.prerecordFrames);
	appSettings.setValue("camera/segmentLengthFrames",  self.imagerSettings.segmentLengthFrames);
	appSettings.setValue("camera/segments",             self.imagerSettings.segments);
	}
'''


		#TODO do this properly


	# self.SetLiveTiming()




# NumPy stuff











'''
	Camera::setRecSequencerModeSingleBlock
	  Camera::setRecRegionEndWords
		59
	  Camera::writeSeqPgmMemory
		60 - 61
	  Camera::setFrameSizeWords
		62
	Camera::startRecording
	  Camera::startSequencer
		63 - 64
	  Camera::setShutterGatingEnable
	   65
'''


