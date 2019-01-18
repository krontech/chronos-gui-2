

from memobj import MemObject

FRAME_SIZE = 1280 * 1024 * 12 // 8
mem = MemObject()


cr = mem.FPGARead16("DISPLAY_CTL") | 1	
mem.FPGAWrite16nb("DISPLAY_CTL", cr) #Set to display from display frame address register
mem.FPGAWrite32nb("DISPLAY_FRAME_ADDRESS", 0x40000)	# Set display address

print ("Zero image area")
#Zero image area
mem.FPGAWrite32nb("GPMC_PAGE_OFFSET", 0x40000) #Set GPMC offset
for i in range(0, FRAME_SIZE, 2):
	mem.RAMWrite16(i, 123) #(i >> 8) & 0xff80)

print ("Draw a rectangular box with diagonal")
# Draw a rectangular box around the outside of the screen and a diagonal lines starting from the top left
#for(int i = 0; i < 1; i++)
#{

# breakpoint()

def writePixel12(pixel, offset, value):
	# breakpoint()

	address = pixel * 12 // 8 + offset
	shift = (pixel & 0x1) * 4
	dataL = mem.RAMRead8(address)
	dataH = mem.RAMRead8(address+1)

	maskL = 0xff - (0xFF << shift)
	maskH = 0xff - (0xFFF >> (8 - shift))
	dataL &= maskL
	dataH &= maskH

	dataL |= (value << shift) & 0xff
	dataH |= (value >> (8 - shift)) & 0xff
	mem.RAMWrite8(address, dataL)
	mem.RAMWrite8(address+1, dataH)



for y in range(1024): 
	for x in range(1280):	
	
		# self.writePixel12(x+y*1280, 0x2000000, 2048) #(x == 0 || y == 0 || x == 1279 || y == 1023 || x == y) ? 0xFFF : 0);
		d =  ((x == 0) or (y == 0) or (x == 1279) or (y == 1023) or (x == y)) 
		if d:
			writePixel12(x+y*1280, 0x0000000, 0xFFF )
		else:
			writePixel12(x+y*1280, 0x0000000, 0)
		# self.writePixel12(x+y*1280, 0x2000000, ((x == 0) || (y == 0) || (x == 1279) || (y == 1023) || (x == y)) ? 0xFFF : 0);
		# self.writePixel12(x+y*1280, 0x2000000,  (x == y) ? 0xFFF : 0);
		#print(".")
		#qDebug() << "line" << y;
		pass

