from periphery import SPI


# Now set up sensor with SPI

SPI_DEV = "/dev/spidev3.0"
SPI_MODE = 1
SPI_SPEED = 1000000
SPI_BITORDER = "msb"
SPI_BITS = 16

#spi = 0

def spi_open2():
	breakpoint()
	print ("spi_open!!!!")
	global spiobj
	spiobj = SPI(SPI_DEV, SPI_MODE, SPI_SPEED, SPI_BITORDER, SPI_BITS)
	#print (spi)

def spi_transfer(data):
	breakpoint()
	print (f"spi_transfer 0x{data:x}")
	global spiobj
	spilist = [(data >> 8) & 0xff, data & 0xff]
	#print (spilist)
	spiobj.transfer(spilist)
		



class SPIobj:

	spi_obj = SPI(SPI_DEV, SPI_MODE, SPI_SPEED, SPI_BITORDER, SPI_BITS)

	def spi_open3(self):
		print ("spi_open!!!!")
		# spiobj = SPI(SPI_DEV, SPI_MODE, SPI_SPEED, SPI_BITORDER, SPI_BITS)
		#print (spi)

	def spi_transfer3(self, data):
		print (f"-->spi_transfer 0x{data:x}")
		# global spiobj
		# spilist = [(data >> 8) & 0xff, data & 0xff]
		spilist = [data & 0xff, (data >> 8) & 0xff]
		#print (spilist)
		self.spi_obj.transfer(spilist)

