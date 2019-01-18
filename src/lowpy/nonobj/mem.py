import time

from periphery import MMIO
#import spidev
#from periphery import SPI
from mmapregisters import *
from spi import *
from lux import *

# Open FPGA memory map
fpga_mmio = MMIO(0x01000000, 0x3000)

def mm_write16(addr, data):
    fpga_mmio.write16(addr, data)

def mm_write32(addr, data):
    fpga_mmio.write32(addr, data)

def nicehex(n):
    return "0x" + ("0000000" + hex(n)[2:])[-4:]
def nicehex4(n):
    return "0x" + ("0000000" + hex(n)[2:])[-8:]

print ("FPGA registers")

for i in range(0, 128, 4):
    mm = fpga_mmio.read32(i)
    print (nicehex(i), " - ", nicehex4(mm))

for i in range(1024, 1024+126, 4):
    mm = fpga_mmio.read32(i)
    print (nicehex(i), " - ", nicehex4(mm))

mm = fpga_mmio.read32(28)
print (nicehex(28), nicehex4(mm))




#print ((IMAGER_FRAME_PERIOD_ADDR))
#print (fpga_mmio.read32(IMAGER_FRAME_PERIOD_ADDR))

#fpga_mmio.write32(IMAGER_FRAME_PERIOD_ADDR, 100*4000)	#Disable integration
mm_write32(IMAGER_FRAME_PERIOD_ADDR, 100*4000)	#Disable integration
mm_write32(IMAGER_INT_TIME_ADDR, 100*4100)

print (fpga_mmio.read32(IMAGER_INT_TIME_ADDR))


# Set up DAC with SPI
def luxSetReset(value):
	readvalue = fpga_mmio.read16(IMAGE_SENSOR_CONTROL_ADDR)
	if value:
		fpga_mmio.write16(IMAGE_SENSOR_CONTROL_ADDR, readvalue | IMAGE_SENSOR_RESET_MASK)
	else:
		fpga_mmio.write16(IMAGE_SENSOR_CONTROL_ADDR, readvalue & ~IMAGE_SENSOR_RESET_MASK)

	#gpmc->write16(IMAGE_SENSOR_CONTROL_ADDR, (gpmc->read16(IMAGE_SENSOR_CONTROL_ADDR) & ~IMAGE_SENSOR_RESET_MASK) | (reset ? IMAGE_SENSOR_RESET_MASK : 0));
	

initDAC()

writeDACVoltages()


# Now do rest of lux init
time.sleep(0.01)


luxSetReset(True)
luxSetReset(False)

time.sleep(0.001)





fpga_mmio.close()
