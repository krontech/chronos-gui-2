from periphery import SPI


# Now set up sensor with SPI

SPI_DEV = "/dev/spidev3.0"
SPI_MODE = 1
SPI_SPEED = 1000000
SPI_BITORDER = "msb"
SPI_BITS = 16

spi = 0

def spi_open():
	global spi
	spi = SPI(SPI_DEV, SPI_MODE, SPI_SPEED, SPI_BITORDER, SPI_BITS)
	print (spi)

def spi_transfer(data):
	global spi
	spilist = [data >> 8, data & 255]
	print (spilist)
	spi.transfer(spilist)

