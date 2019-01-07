
import time
import pdb
from termcolor import cprint

from periphery import MMIO
from periphery import GPIO

#import spidev
#from periphery import SPI
from mmapregisters import *
from spi import *
from lux import *
from ctypes import *



def nicehex(n):
	return "0x" + ("0000000" + hex(n)[2:])[-4:]
def nicehex4(n):
	return "0x" + ("0000000" + hex(n)[2:])[-8:]




class MemObject:
	#print ("Created!")
	FPGAc = 0  # how many FPGA writes

	FPGAcol = "green"
	FPGAcol_old = "red"

	breakFPGA = False
	# breakFPGA = True

	fpga_mmio = MMIO(0x01000000, 0x3000)
	RAM_mmio = MMIO(0x02000000, 0x1000000)    

	ptr = fpga_mmio.pointer
	print(f"ptr is {ptr}")
	print(f"base is {fpga_mmio.base}")

	FPGAlptr = cast(ptr, POINTER(c_ulong))
	FPGAwptr = cast(ptr, POINTER(c_ushort))
	FPGAbptr = cast(ptr, POINTER(c_ubyte))

	# breakpoint()

	FPGActypes = True
	# FPGActypes = False

	print ("Testing RAM R/W")
	x = RAM_mmio.read8(0)
	print (f" - reading {x}")
	print (" - writing...")
	RAM_mmio.write8(0, 123)
	x = RAM_mmio.read8(0)
	print (f" - reading {x}")

	def CtypesTest(self):
		# ptr = self.fpga_mmio.pointer
		# print(f"ptr is {ptr}")
		# print(f"base is {self.fpga_mmio.base}")

		# lptr = cast(ptr, POINTER(c_ulong))
		# wptr = cast(ptr, POINTER(c_ushort))
		# bptr = cast(ptr, POINTER(c_ubyte))
		
		# lptr[2] = 0x0fc1
		# bptr[0] = 5
		# self.FPGAlptr[0x428//4] = 0x510
		# self.FPGAlptr[0] = 0x123
		print(f"\n0x0: 0x{self.FPGAlptr[0x0]:x}")


		print("################\n32 bit:")
		for i in range(0x0, 0x430//4):
			print(f"  0x{4*i:x}: 0x{self.FPGAlptr[i]:x}")
		print("16 bit:")
		for i in range(20):
			print(f"  0x{2*i:x}: 0x{self.FPGAwptr[i]:x}")
		print("8 bit")
		for i in range(40):
			print(f"  0x{i:x}: 0x{self.FPGAbptr[i]:x}")

		print(f"\n0x428: 0x{self.FPGAlptr[0x428//4]:x}")

	def __init__(self):
		pass
		# breakpoint()
	

		# print ("Testing RAM R/W")
		# x = self.RAM_mmio.read8(0)
		# print (f" - reading {x}")
		# print (" - writing...")
		# self.mem.RAMWrite8(0, 123)
		# x = self.RAM_mmio.read8(0)
		# print (f" - reading {x}")

	


	
	# don't use these ones
	# def mm_write16(self, addr, data):
	# 	self.fpga_mmio.write16(addr, data)

	# def mm_write32(self, addr, data):
	# 	self.fpga_mmio.write32(addr, data)


	#NEW: use Python dictionary to do FPGA writes

	def FPGAWrite8(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		FPGAreg = FPGA_dict[addr]
		cprint (f'   ({self.FPGAc})--- FPGAWrite8("{addr}":0x{FPGAreg:x}, 0x{data:x})', self.FPGAcol)
		if self.breakFPGA: breakpoint()
		if self.FPGActypes:
			self.FPGAbptr[FPGAreg] = data & 0xff
		else:
			self.fpga_mmio.write8(FPGAreg, data)

	def FPGAWrite16(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		FPGAreg = FPGA_dict[addr]
		cprint (f'   ({self.FPGAc})--- FPGAWrite16("{addr}":0x{FPGAreg:x}, 0x{data:x})', self.FPGAcol)
		if self.breakFPGA: breakpoint()
		if self.FPGActypes:
			self.FPGAwptr[FPGAreg // 2] = data & 0xffff
		else:
			self.fpga_mmio.write16(FPGAreg, data)

	def FPGAWrite32(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		FPGAreg = FPGA_dict[addr]
		cprint (f'   ({self.FPGAc})--- FPGAWrite32("{addr}":0x{FPGAreg:x}, 0x{data:x})', self.FPGAcol)
		if self.breakFPGA: breakpoint()
		if self.FPGActypes:
			self.FPGAlptr[FPGAreg // 4] = data
		else:
			self.fpga_mmio.write32(FPGAreg, data)


#duplicate functions without debug, for SCI writes

	def FPGAWrite8s(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		FPGAreg = FPGA_dict[addr] * 1
		if self.FPGActypes:
			self.FPGAbptr[FPGAreg] = data & 0xff
		else:
			self.fpga_mmio.write8(FPGAreg, data)

	def FPGAWrite16s(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		FPGAreg = FPGA_dict[addr] * 1
		if self.FPGActypes:
			self.FPGAwptr[FPGAreg // 2] = data & 0xffff
		else:
			self.fpga_mmio.write16(FPGAreg, data)

	def FPGAWrite32s(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		FPGAreg = FPGA_dict[addr] * 1
		if self.FPGActypes:
			self.FPGAlptr[FPGAreg // 4] = data 
		else:
			self.fpga_mmio.write32(FPGAreg, data)



	def FPGARead16(self, addr):
		FPGAreg = FPGA_dict[addr] * 1
		if self.FPGActypes:
			ret = self.FPGAwptr[FPGAreg // 2]
		else:
			ret = self.fpga_mmio.read16(FPGAreg)
		return ret

	def FPGARead32(self, addr):
		FPGAreg = FPGA_dict[addr] * 1
		if self.FPGActypes:
			ret = self.FPGAlptr[FPGAreg // 4]
		else:
			ret = self.fpga_mmio.read32(FPGAreg)
		return ret





	#OLDER non-Pythonic: use these three functions to write to the (16 bit) FPGA address
	def fpga_write8(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		cprint (f"   ({self.FPGAc})--- fpga_write8(0x{1 * addr:x}, 0x{data:x})", self.FPGAcol_old)
		if self.breakFPGA: breakpoint()
		if self.FPGActypes:
			self.FPGAbptr[addr] = data & 0xff
		else:
			self.fpga_mmio.write8(1 * addr, data)

	def fpga_write16(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		cprint (f"   ({self.FPGAc})--- fpga_write16(0x{1 * addr:x}, 0x{data:x})", self.FPGAcol_old)
		if self.breakFPGA: breakpoint()
		if self.FPGActypes:
			self.FPGAwptr[addr // 2] = data & 0xffff
		else:
			self.fpga_mmio.write16(1 * addr, data)

	def fpga_write32(self, addr, data):
		self.FPGAc = self.FPGAc + 1
		cprint (f"   ({self.FPGAc})--- fpga_write32(0x{1 * addr:x}, 0x{data:x})", self.FPGAcol_old)
		if self.breakFPGA: breakpoint()
		if self.FPGActypes:
			self.FPGAlptr[addr // 4] = data 
		else:
			self.fpga_mmio.write32(1 * addr, data)


#duplicate functions without debug, for SCI writes
	def fpga_write8s(self, addr, data):
		if self.FPGActypes:
			self.FPGAbptr[addr] = data & 0xff
		else:
			self.fpga_mmio.write8(1 * addr, data)

	def fpga_write16s(self, addr, data):
		if self.FPGActypes:
			self.FPGAwptr[addr // 2] = data & 0xffff
		else:
			self.fpga_mmio.write16(1 * addr, data)

	def fpga_write32s(self, addr, data):
		if self.FPGActypes:
			self.FPGAlptr[addr // 4] = data
		else:
			self.fpga_mmio.write32(1 * addr, data)





	def fpga_read32(self, addr):
		# print (f"   $$$ fpga_read32(0x{2 * addr:x})")
		res = self.fpga_mmio.read32(1 * addr)
		# print (f"    ->0x{res:x}")
		return res

	def fpga_read16(self, addr):
		# print (f"   $$$ fpga_read16(0x{2 * addr:x})")
		res = self.fpga_mmio.read16(1 * addr)
		# print (f"    ->0x{res:x}")
		return res



# RAM access




	def RAMWrite8(self, addr, data):
		self.RAM_mmio.write8(addr, data)

	def RAMWrite16(self, addr, data):
		self.RAM_mmio.write16(addr, data)

	def RAMRead8(self, addr):
		res = self.RAM_mmio.read8(addr)
		return res



	def mm_open(self):
		# Open FPGA memory map
		#rint("Open!")
		# self.fpga_write32(IMAGER_FRAME_PERIOD, 100*4000)  #Disable integration
		# self.fpga_write32(IMAGER_INT_TIME, 100*4100)

		#print (self.fpga_mmio.read32(IMAGER_INT_TIME_ADDR))
		pass

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


	def GPIOWrite(self, pin_name, value):
		gpio = self._GPIO_ports[pin_name]
		gpio.write(bool(value))

	def GPIORead(self, pin_name):
		gpio = self._GPIO_ports[pin_name]
		return gpio.read()


	_board_chronos14_gpio = {
	"lux1310-dac-cs" : (33, "out"),
	"lux1310-color" :  (66, "in"),
	"encoder-a" :      (20, "in"),
	"encoder-b" :      (26, "in"),
	"encoder-sw" :     (27, "in"),
	"shutter-sw" :     (66, "in"),
	"record-led.0" :   (41, "out"),
	"record-led.1" :   (25, "out"),
	"trigger-pin" :    (127, "in"),
	"frame-irq" :      (51, "in"),
	# FPGA Programming Pins 
	# "ecp5-progn" :     (47, ""),
	# "ecp5-init" :      (45, ""),
	# "ecp5-done" :      (52, ""),
	# "ecp5-cs" :        (58, ""),
	# "ecp5-holdn" :     (58  ""),
	}

	_GPIO_ports = {}

	for key, value in _board_chronos14_gpio.items():
		gpioaccess = GPIO(value[0], value[1])
		_GPIO_ports.update({key : gpioaccess})

	#print(_GPIO_ports)




#fpga_mmio.close()
