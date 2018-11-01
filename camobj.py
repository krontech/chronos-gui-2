
# Camera class
#from mem import fpga_mmio
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
	def __init__(self):
		print ("CamObject Init")
		self.CamInit()


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
		print("!!!!!")
		self.sensor.OpsDict["SetPeriod"](self, 1000000)
		self.sensor.OpsDict["SetExposure"]()
		self.sensor.OpsDict["CalSuffix"]()
		self.sensor.OpsDict["SetGain"](self, 12)
		
		# self.CamInit()

	def SetLiveTiming(self, geometry, hOutRes, vOutRes, maxFPS):

		pxClock = 100000000
		hSync = 50
		hPorch = 166
		vSync = 3
		vPorch = 38

		hPeriod = hOutRes + hSync + hPorch + hSync

		# Calculate minimum hPeriod to fit within the max vertical
		# resolution and make sure hPeriod is equal to or larger
	 
		minHPeriod = (pxClock / ((sensor.v_max_res + vPorch + vSync + vSync) * maxFps)) + 1; # the +1 is just to round up
		if hPeriod < minHPeriod: 
			hPeriod = minHPeriod

		# calculate vPeriod and make sure it's large enough for the frame
		vPeriod = pxClock / (hPeriod * maxFps)
		if vPeriod < (vOutRes + vSync + vPorch + vSync):
			vPeriod = vOutRes + vSync + vPorch + vSync
	
		# calculate FPS for debug output
		fps = pxClock / (vPeriod * hPeriod)
		print ("Timing: %d*%d@%d (%d*%d max: %d)\n", \
			   (hPeriod - hSync - hPorch - hSync), (vPeriod - vSync - vPorch - vSync), \
			   fps, hOutRes, vOutRes, maxFps)

	 
	def CamInit(self):
		
		print (self.sensor)

		print (f"pixel rate is {self.sensor.ImageSensor.pixel_rate}")
		 
		maxfps = self.sensor.ImageSensor.pixel_rate / \
			(self.sensor.ImageSensor.h_max_res * self.sensor.ImageSensor.v_max_res);
		print (f"maxfps is {maxfps}")

		# Configure the FIFO threshold and image sequencer

		self.mem.fpga_write32(SEQ_LIVE_ADDR_0, MAX_FRAME_LENGTH)
		self.mem.fpga_write32(SEQ_LIVE_ADDR_1, MAX_FRAME_LENGTH * 2)
		self.mem.fpga_write32(SEQ_LIVE_ADDR_2, MAX_FRAME_LENGTH * 3)
		self.mem.fpga_write32(SEQ_REC_REGION_START, MAX_FRAME_LENGTH * 3)



	print ("begin")
	mem = MemObject()
	#sensor = SensorObject(mem)
	sensor = Lux1310Object(mem)

	
	ioports = board_chronos14_ioports

	# self.CamInit()


	ReadSerial()




	# self.SetLiveTiming()




# minHPeriod;
# hPeriod;
# vPeriod;
# fps;


# def cam_init(cam):

# 	frame_words = 0
# 	maxfps = 3




#print ("cam begin")

#camobj = CamObject()

#camobj.mem.mm_print()
