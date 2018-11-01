
from sensorobj import SensorObject
import spi
from lux1310h import *
from mmapregisters import *
import time
from dataclasses import dataclass
import struct
from lux1310waves import *
from lux1310sensor import *

'''
#convert this to Struct.struct
@dataclass
class FPGA1310Sensor:

	control = 0
	clk_phase = 0
	sync_token = 0
	data_correct = 0
	fifo_start = 0
	fifo_stop = 0
	__reserved = 0
	frame_period = 0
	int_tim = 0
	sci_control = 0
	sci_address = 0
	sci_datalen = 0
	sci_fifo_addr = 0
	sci_fifo_data = 0

'''






class Lux1310Object(SensorObject):



	# Gain parameters
	Lux1310GainData = [
		{   # x1 - 0dB 
			"vrstb": 2700,
			"vrst": 3300,
			"vrsth": 3600,
			"sampling": 0x7f,
			"feedback": 0x7f,
			"gain_bit": 3,
			"analog_gain": 0,
		},
		{ # x2 - 6dB 
			"vrstb": 2700,
			"vrst": 3300,
			"vrsth": 3600,
			"sampling": 0xfff,
			"feedback": 0x7f,
			"gain_bit": 3,
			"analog_gain": 6,
		},
		{ # x4 - 12dB 
			"vrstb": 2700,
			"vrst": 3300,
			"vrsth": 3600,
			"sampling": 0xfff,
			"feedback": 0x7f,
			"gain_bit": 0,
			"analog_gain": 12,
		},
		{ # x8 - 18dB 
			"vrstb": 1700,
			"vrst": 2300,
			"vrsth": 2600,
			"sampling": 0xfff,
			"feedback": 0x7,
			"gain_bit": 0,
			"analog_gain": 18,
		},
		{ # x16 - 24dB 
			"vrstb": 1700,
			"vrst": 2300,
			"vrsth": 2600,
			"sampling": 0xfff,
			"feedback": 0x1,
			"gain_bit": 0,
			"analog_gain": 24,
		}
	]

	def Lux1310SCIWrite(self, addr, value):
		pass


	def FPGAAndBits(self, addr, mask):
		readdata = self.fpga_read16(addr)
		readdata &= mask
		self.fpga_write16(addr, readdata)

	def FPGAOrBits(self, addr, mask):
		readdata = self.fpga_read16(addr)
		readdata |= mask
		self.fpga_write16(addr, readdata)

	def Lux1310SCIWrite(self, addr, value):
		'''Perform a simple 16bit register write'''
		# Clear RW, and setup the transfer and fill the FIFO
		FPGAAndBits(SENSOR_SCI_CONTROL, ~SENSOR_SCI_CONTROL_RW_MASK)
		self.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.fpga_write16(SENSOR_SCI_DATALEN, 2)
		self.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, (value >> 8) & 0xff)
		self.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, value & 0xff)

		# Start the transfer and then wait for completion.
		FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

	def Lux1310SCIWriteBuf(self, addr, values):
		'''Perform a series of 8 bit register writes'''
		# Clear RW, and setup the transfer and fill the FIFO
		FPGAAndBits(SENSOR_SCI_CONTROL, ~SENSOR_SCI_CONTROL_RW_MASK)
		self.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.fpga_write16(SENSOR_SCI_DATALEN, len(values))
		for b in values:
			self.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, b)

		# Start the transfer and then wait for completion.
		FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

	def Lux1310SCIRead(self, addr, value):
		'''Perform a simple 16bit register read'''
		# Set RW, address and length.
		FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RW_MASK)
		self.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.fpga_write16(SENSOR_SCI_DATALEN, 2)
		
		# Start the transfer and then wait for completion.
		Lux1310OrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.fpga+read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

		return self.fpga_read16(SENSOR_SCI_READ_DATA)
	

	def Lux1310WriteWaveTab(self, wavedict):
		waves = wavedict["table"]
		#Lux1310Write()

	def lux1310_min_period(self, wavelen):
	
		t_hblank = 2
		t_tx = 25
		t_fovf = 50
		t_fovb = 50 # Duration between PRSTN falling and TXN falling (I think) 
		
		#print (self)
		
		g = self.ImageGeometry
		# Sum up the minimum number of clocks to read a frame at this resolution 
		t_read = (g.hres / LUX1310_HRES_INCREMENT)
		t_row = max(t_read + t_hblank, wavelen + 3)
		print (f"comparing {t_read + t_hblank} and {wavelen + 3}")
		minperiod =  (t_row * g.vres) + t_tx + t_fovf + t_fovb
		# print (f" minperiod = {minperiod}")
		return minperiod

	def Lux1310SetExposure():
		print ("Lux1310SetExposure")

	def Lux1310SetPeriod(self, nsec):
		print (f"Lux1310SetPeriod: {nsec}")
		t_frame = ((nsec * LUX1310_TIMING_CLOCK_RATE) + 999999999) / 1000000000
		print (f" t_frame = {t_frame}")
		
		self.mem.fpga_write32(IMAGER_FRAME_PERIOD, int(t_frame))
		for i in Lux1310WaveTables:
			# if t_frame >= self.lux1310_min_period(i[""])
			#print (i["read_delay"])
			min_period = self.sensor.lux1310_min_period(i["read_delay"])
			print (f"{i['read_delay']}: min period is {min_period}")
			if t_frame >= min_period:
				self.sensor.Lux1310WriteWaveTab(i)
				break
		
	def Lux1310SetResolutions():
		pass

	def Lux1310GetConstraints():
		pass

	def Lux1310SetGain(self, gain):
		print (f"Lux1310SetGain: {gain}")
		for gdict in self.sensor.Lux1310GainData:
			if gdict["analog_gain"] == gain:
				print (gdict)
				break
		pass

	def Lux1310CalGain():
		pass

	def Lux1310CalSuffix():
		pass




	Lux1310OpsDict = {
		"SetExposure": Lux1310SetExposure,
		"SetPeriod": Lux1310SetPeriod,
		"SetResolutions": Lux1310SetResolutions,
		"GetConstraints": Lux1310GetConstraints,
		"SetGain": Lux1310SetGain,
		"CalGain": Lux1310CalGain,
		"CalSuffix": Lux1310CalSuffix
	}


	OpsDict = Lux1310OpsDict

	# print ("class SO")
	def lux1310num(self):
		return 77

#	lux1310num()


	def __init__(self, mem):
		SensorObject.__init__(self)
		self.mem = mem
		self.lux1310num()
		self.initlux1310()		
		self.SensorInit()
		#self.OpsDict = Lux1310OpsDict
		print ("Lux1310 initialized!")


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

		print ("initlux1310")

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
		readvalue = self.mem.fpga_mmio.read16(IMAGE_SENSOR_CONTROL)
		if value:
			self.mem.fpga_write16(IMAGE_SENSOR_CONTROL, readvalue | IMAGE_SENSOR_RESET_MASK)
		else:
			self.mem.fpga_write16(IMAGE_SENSOR_CONTROL, readvalue & ~IMAGE_SENSOR_RESET_MASK)

	def SensorInit(self):
		#self.ImageSensor = ImageSensorData()
		self.ImageSensor.name = "lux1310"
		self.ImageSensor.mfr = "Luxima";
		self.ImageSensor.h_max_res = 1280;
		self.ImageSensor.v_max_res = 1024;
		self.ImageSensor.h_min_res = 336;
		self.ImageSensor.v_min_res = 96;
		self.ImageSensor.h_increment = LUX1310_HRES_INCREMENT;
		self.ImageSensor.v_increment = 2;
		self.ImageSensor.pixel_rate = self.ImageSensor.h_max_res * self.ImageSensor.v_max_res * 1057;
		self.ImageSensor.adc_count = LUX1310_ADC_COUNT;


