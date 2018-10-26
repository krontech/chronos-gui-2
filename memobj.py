import time

from periphery import MMIO
#import spidev
#from periphery import SPI
from mmapregisters import *
from spi import *
from lux import *


def nicehex(n):
	return "0x" + ("0000000" + hex(n)[2:])[-4:]
def nicehex4(n):
	return "0x" + ("0000000" + hex(n)[2:])[-8:]


class MemObject:
	#print ("Created!")
	fpga_mmio = MMIO(0x01000000, 0x3000)

	def mm_write16(self, addr, data):
		self.fpga_mmio.write16(addr, data)

	def mm_write32(self, addr, data):
		self.fpga_mmio.write32(addr, data)

	def mm_open(self):
		# Open FPGA memory map
		#rint("Open!")
		self.mm_write32(IMAGER_FRAME_PERIOD_ADDR, 100*4000)  #Disable integration
		self.mm_write32(IMAGER_INT_TIME_ADDR, 100*4100)

		#print (self.fpga_mmio.read32(IMAGER_INT_TIME_ADDR))

	def mm_print(self):
		print ("FPGA registers")

		for i in range(0, 12, 4):
			mm = self.fpga_mmio.read32(i)
			print (nicehex(i), " - ", nicehex4(mm))

		for i in range(1024, 1024+12, 4):
			mm = self.fpga_mmio.read32(i)
			print (nicehex(i), " - ", nicehex4(mm))

		mm = fpga_mmio.read32(28)
		#print (nicehex(28), nicehex4(mm))





#fpga_mmio.close()
