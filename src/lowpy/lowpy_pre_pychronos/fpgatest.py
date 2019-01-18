
import time
import pdb
from termcolor import cprint
import gc

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

"""
print ("Testing RAM R/W")
x = RAM_mmio.read8(0)
print (f" - reading {x}")
print (" - writing...")
RAM_mmio.write8(0, 123)
x = RAM_mmio.read8(0)
print (f" - reading {x}")
"""




i = 0
size = 2
ctype = 0
FPGAreg = 0
data = 0

if size == 4:
	print("32 bit:")
	# print(f"  0x{4*i:x}: 0x{FPGAlptr[i]:x}")
	if ctype:
		FPGAlptr[i] = 0
	else:
		fpga_mmio.write32(FPGAreg, data)


if size == 2:
	print("16 bit:")
	# print(f"  0x{2*i:x}: 0x{FPGAwptr[i]:x}")
	if ctype:
		FPGAwptr[i] = 0
	else:
		fpga_mmio.write16(FPGAreg, data)

if size == 1:
	print("8 bit")
	# print(f"  0x{i:x}: 0x{FPGAbptr[i]:x}")
	if ctype:
		FPGAbptr[i] = 0
	else:
		fpga_mmio.write8(FPGAreg, data)

gc.collect()



