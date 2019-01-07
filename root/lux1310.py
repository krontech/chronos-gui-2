
from sensorobj import SensorObject
import spi
from lux1310h import *
import time

class Lux1310Object(SensorObject):

	def lux1310num(self):
		return 77

#	lux1310num()


	def __init__(self, mem):
		self.mem = mem
		self.lux1310num()
		self.initlux1310()		


	#numfunc = lux1310num


	def setDACCS(self, flag):
		pass	




	def writeDACVoltage(self, chan, voltage):
		if chan == VDR3_VOLTAGE:
			self.writeDAC(voltage * VDR3_SCALE, VDR3_VOLTAGE)
		elif chan == VABL_VOLTAGE:
			self.writeDAC(voltage * VABL_SCALE, VABL_VOLTAGE)
		elif chan == VDR1_VOLTAGE:
			self.writeDAC(voltage * VDR1_SCALE, VDR1_VOLTAGE)
		elif chan == VDR2_VOLTAGE:
			self.writeDAC(voltage * VDR2_SCALE, VDR2_VOLTAGE)
		elif chan == VRSTB_VOLTAGE:
			self.writeDAC(voltage * VRSTB_SCALE, VRSTB_VOLTAGE)
		elif chan == VRSTH_VOLTAGE:
			self.writeDAC(voltage * VRSTH_SCALE, VRSTH_VOLTAGE)
		elif chan == VRSTL_VOLTAGE:
			self.writeDAC(voltage * VRSTL_SCALE, VRSTL_VOLTAGE)
		elif chan == VRST_VOLTAGE:
			self.writeDAC(voltage * VRST_SCALE, VRST_VOLTAGE)
		else:
			pass


	def writeDAC(self, data, channel):
		self.writeDACSPI(((int(channel) & 0x7) << 12) | (int(data) & 0x0FFF))


	def writeDACSPI(self, data):
		spi.spi_transfer(data)


	def initDAC(self):
		spi.spi_open()
		spi.spi_transfer(0x9000)

	def writeDACVoltages(self):
		self.initDAC();
		self.writeDACVoltage(VABL_VOLTAGE, 0.3);
		self.writeDACVoltage(VRSTB_VOLTAGE, 2.7);
		self.writeDACVoltage(VRST_VOLTAGE, 3.3);
		self.writeDACVoltage(VRSTL_VOLTAGE, 0.7);
		self.writeDACVoltage(VRSTH_VOLTAGE, 3.6);
		self.writeDACVoltage(VDR1_VOLTAGE, 2.5);
		self.writeDACVoltage(VDR2_VOLTAGE, 2);
		self.writeDACVoltage(VDR3_VOLTAGE, 1.5);






	def initlux1310(self):

		self.mem.mm_open()
		#self.mem.initlux()

		self.initDAC()
		self.writeDACVoltages()


		# Now do rest of lux init
		time.sleep(0.01)


		self.lux1310SetReset(True)
		self.lux1310SetReset(False)

		time.sleep(0.001)



		# Set up DAC with SPI
		def lux1310SetReset(self, value):
			readvalue = self.fpga_mmio.read16(IMAGE_SENSOR_CONTROL_ADDR)
			if value:
				self.fpga_mmio.write16(IMAGE_SENSOR_CONTROL_ADDR, readvalue | IMAGE_SENSOR_RESET_MASK)
			else:
				self.fpga_mmio.write16(IMAGE_SENSOR_CONTROL_ADDR, readvalue & ~IMAGE_SENSOR_RESET_MASK)





'''
def writeDACSPI(data)
{
	UInt8 tx[2];
	UInt8 rx[sizeof(tx)];
	int retval;

	tx[1] = data >> 8;
	tx[0] = data & 0xFF;

	setDACCS(false);
	//delayms(1);
	retval = spi->Transfer((uint64_t) tx, (uint64_t) rx, sizeof(tx));
	//delayms(1);
	setDACCS(true);
	return retval;
}

'''
