
from periphery import GPIO
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

# Bit hacking to extract a value from a bitmask and shift it down.
def getbits(value, mask):

	if mask == 0:
		print (0)
		return 0	
	else:
		lsb = (~mask + 1) & mask
		print ( (value & mask) / lsb)
		return (value & mask) / lsb
	
# Bit hacking to shift a value up to the position specified by the mask. 
def setbits(value, mask):
	print(f"Setbits ({value}, {mask}):")
	if mask == 0:
		print (0)
		return 0
	else: 
		lsb = (~mask + 1) & mask
		print ( (value * lsb) & mask)
		return (value * lsb) & mask


class Lux1310Object(SensorObject):

	#we'll keep a copy of the wavetable delay
	keepdelay = 0;

	#get SCI constants
	SCI = SCIObject()

	# SPI_DEV = "/dev/spidev3.0"
	# SPI_MODE = 1
	# SPI_SPEED = 1000000
	# SPI_BITORDER = "msb"
	# SPI_BITS = 16

	# spi = SPI(SPI_DEV, SPI_MODE, SPI_SPEED, SPI_BITORDER, SPI_BITS)
	


	def _Lux1310ClocksToNsec(self, _clks, _hz):
		return ((_clks * 1000000000) + _hz - 1) / _hz
	
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



	def FPGAAndBits(self, addr, mask):
		readdata = self.mem.fpga_read16(addr)
		readdata &= mask
		self.mem.fpga_write16(addr, readdata)

	def FPGAOrBits(self, addr, mask):
		readdata = self.mem.fpga_read16(addr)
		readdata |= mask
		self.mem.fpga_write16(addr, readdata)

	def Lux1310SCIWrite(self, addr, value):
		'''Perform a simple 16bit register write'''
		# Clear RW, and setup the transfer and fill the FIFO
		self.FPGAAndBits(SENSOR_SCI_CONTROL, ~SENSOR_SCI_CONTROL_RW_MASK)
		self.mem.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.mem.fpga_write16(SENSOR_SCI_DATALEN, 2)
		self.mem.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, (value >> 8) & 0xff)
		self.mem.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, value & 0xff)

		# Start the transfer and then wait for completion.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

	def Lux1310SCIWriteBuf(self, addr, values):
		'''Perform a series of 8 bit register writes'''
		# Clear RW, and setup the transfer and fill the FIFO
		self.FPGAAndBits(SENSOR_SCI_CONTROL, ~SENSOR_SCI_CONTROL_RW_MASK)
		self.mem.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.mem.fpga_write16(SENSOR_SCI_DATALEN, len(values))
		for b in values:
			self.mem.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, b)

		# Start the transfer and then wait for completion.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

	def Lux1310SCIRead(self, addr):
		'''Perform a simple 16bit register read'''
		# Set RW, address and length.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RW_MASK)
		self.mem.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.mem.fpga_write16(SENSOR_SCI_DATALEN, 2)
		
		# Start the transfer and then wait for completion.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

		return self.mem.fpga_read16(SENSOR_SCI_READ_DATA)
	
	def Lux1310Read(self, reg):
		val = self.Lux1310SCIRead(reg >> self.SCI.LUX1310_SCI_REG_ADDR)
		return getbits(val, reg & self.SCI.LUX1310_SCI_REG_MASK)

	def Lux1310Write(self, reg, val):
		'''Perform a simple register write, which contains only one sub-field.'''
		print(f"Lux1310Write({reg}, {val})")
		sciaddr = reg >> self.SCI.LUX1310_SCI_REG_ADDR
		scidata = setbits(val, reg & self.SCI.LUX1310_SCI_REG_MASK)
		self.Lux1310SCIWrite(sciaddr, scidata)


	def Lux1310WriteWaveTab(self, wavedict):
		self.keepdelay = wavedict["read_delay"]
		waves = wavedict["table"]
		self.Lux1310Write(self.SCI.LUX1310_SCI_TIMING_EN, 0)
		delay =wavedict["read_delay"]
		self.Lux1310Write(self.SCI.LUX1310_SCI_RDOUT_DLY, delay)
		self.Lux1310Write(self.SCI.LUX1310_SCI_WAVETAB_SIZE, delay)
		self.Lux1310SCIWriteBuf(0x7F, waves);
		self.Lux1310Write(self.SCI.LUX1310_SCI_TIMING_EN, 1)


	def Lux1310MinPeriod(self, wavelen):
	
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

	def Lux1310SetExposure(self, nsec):
		print ("Lux1310SetExposure")
		g = self.ImageGeometry
		t_line = max((g.hres / LUX1310_HRES_INCREMENT)+2, (self.keepdelay + 3))
		t_exposure = (nsec * LUX1310_SENSOR_CLOCK_RATE + 500000000) / 1000000000
		t_start = LUX1310_MAGIC_ABN_DELAY;

		
		# Set the exposure time in units of FPGA timing clock periods, while keeping the
		# exposure as a multiple of the horizontal readout time (to fix the horizontal
		# line issue.
		 
		exp_lines = (t_exposure + t_line/2) / t_line
		int_time = int((t_start + (t_line * exp_lines)) * LUX1310_TIMING_CLOCK_RATE / LUX1310_SENSOR_CLOCK_RATE)
		self.mem.fpga_write32(IMAGER_INT_TIME, int_time)
		

	def Lux1310SetPeriod(self, nsec):
		print (f"Lux1310SetPeriod: {nsec}")
		t_frame = ((nsec * LUX1310_TIMING_CLOCK_RATE) + 999999999) / 1000000000
		print (f" t_frame = {t_frame}")
		
		self.mem.fpga_write32(IMAGER_FRAME_PERIOD, int(t_frame))
		for i in Lux1310WaveTables:
			# if t_frame >= self.lux1310_min_period(i[""])
			#print (i["read_delay"])
			min_period = self.Lux1310MinPeriod(i["read_delay"])
			print (f"{i['read_delay']}: min period is {min_period}")
			if t_frame >= min_period:
				self.Lux1310WriteWaveTab(i)
				break
		
	def Lux1310SetResolutions(self):
		g = self.ImageGeometry
		print(g)
		h_start = int(g.hoffset / LUX1310_HRES_INCREMENT)
		h_width = int(g.hres / LUX1310_HRES_INCREMENT)
		print (h_start)
		print (h_width)
		self.Lux1310Write(self.SCI.LUX1310_SCI_X_START, LUX1310_BLACK_COLS + h_start * LUX1310_HRES_INCREMENT);
		self.Lux1310Write(self.SCI.LUX1310_SCI_X_END, LUX1310_BLACK_COLS + (h_start + h_width) * LUX1310_HRES_INCREMENT - 1)
		self.Lux1310Write(self.SCI.LUX1310_SCI_Y_START, g.voffset)
		self.Lux1310Write(self.SCI.LUX1310_SCI_Y_END, g.voffset + g.vres - 1)
		return 0
		

	def Lux1310GetConstraints(self):
		g = self.ImageGeometry
		c = self.ImageConstraints
		t_line = max((g.hres / LUX1310_HRES_INCREMENT)+2, (LUX1310_MIN_WAVETABLE_SIZE + 3))

		c.t_max_period = 2**32 - 1
		c.t_min_period = self._Lux1310ClocksToNsec(self.Lux1310MinPeriod( LUX1310_MIN_WAVETABLE_SIZE), LUX1310_TIMING_CLOCK_RATE)
		c.f_quantization = LUX1310_TIMING_CLOCK_RATE

		c.t_min_exposure = self._Lux1310ClocksToNsec(t_line, LUX1310_TIMING_CLOCK_RATE);
		c.t_max_shutter = 360
		c.t_exposure_delay = self._Lux1310ClocksToNsec(LUX1310_MAGIC_ABN_DELAY, LUX1310_TIMING_CLOCK_RATE)

		return 0;

	def Lux1310SetGain(self, gain):
		print (f"Lux1310SetGain: {gain}")
		for gdict in self.Lux1310GainData:
			if gdict["analog_gain"] == gain:
				self.Lux1310SetVoltage(VRSTB_VOLTAGE, gdict["vrstb"], 1, 1)
				self.Lux1310SetVoltage(VRST_VOLTAGE, gdict["vrst"], LUX1310_VRST_MUL, LUX1310_VRST_DIV)
				#NOTE: this uses LUX1310_VRST_DIV in camm-daemon:
				self.Lux1310SetVoltage(VRST_VOLTAGE, gdict["vrsh"], LUX1310_VRST_MUL, LUX1310_VRSTH_DIV)


				self.Lux1310Write(self.SCI.LUX1310_SCI_GAIN_SEL_SAMP, gdict["sampling"])
				self.Lux1310Write(self.SCI.LUX1310_SCI_GAIN_SEL_FB, gdict["feedback"])
				self.Lux1310Write(self.SCI.LUX1310_SCI_GAIN_BIT, gdict["gain_bit"])

			# "vrstb": 2700,
			# "vrst": 3300,
			# "vrsth": 3600,
			# "sampling": 0x7f,
			# "feedback": 0x7f,
			# "gain_bit": 3,
			# "analog_gain": 0,

				#TODO: use an actual cal file

				# /* Adjust the ADC offsets if calibration data is provided. */
				# if (calfile) {
				#     fread(caldata, sizeof(caldata[0]), LUX1310_ADC_COUNT, calfile);
				# } else {
				#     memset(caldata, 0, sizeof(caldata));
				# }


				# for j in range(LUX1310_ADC_COUNT)
				for j in range(self.adc_count):
				    Lux1310Write(self.SCI.LUX1310_SCI_ADC_OS[j], 0)
				# for (j = 0; j < sensor->adc_count; j++) {
				#     uint16_t x = abs(caldata[j]) & ((1 << LUX1310_ADC_OFFSET_BITS) - 1);
				#     if (caldata[j]) x |= (1 << LUX1310_ADC_OFFSET_BITS);
				#     lux1310_write(data, LUX1310_SCI_ADC_OS(j), x);

				
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
		#self.cam = cam
		#self.lux1310num()
		self.Lux1310Init()		
		#self.SensorInit()
		#self.OpsDict = Lux1310OpsDict
		print ("Lux1310 initialized!")

		self.Lux1310Write(self.SCI.LUX1310_SCI_LINE_VALID_DLY, 7)
		self.Lux1310Write(self.SCI.LUX1310_SCI_STATE_IDLE_CTRL0, 0xe08e)
		self.Lux1310Write(self.SCI.LUX1310_SCI_STATE_IDLE_CTRL1, 0xfc1f)
		self.Lux1310Write(self.SCI.LUX1310_SCI_STATE_IDLE_CTRL2, 0x0003)
		self.Lux1310Write(self.SCI.LUX1310_SCI_ADC_CLOCK_CTRL, 0x2202)
		self.Lux1310Write(self.SCI.LUX1310_SCI_SEL_VCMI, 6)
		self.Lux1310Write(self.SCI.LUX1310_SCI_SEL_VCMO, 7)
		self.Lux1310Write(self.SCI.LUX1310_SCI_SEL_VCMP, 11)
		self.Lux1310Write(self.SCI.LUX1310_SCI_SEL_VCMN, 4)
		self.Lux1310Write(self.SCI.LUX1310_SCI_INT_CLK_TIMING, 0x41f);



		# Grab the sensor revision for further tuning.
		rev = self.Lux1310Read(self.SCI.LUX1310_SCI_REV_CHIP)
		print(f"configuring for LUX1310 silicon rev {rev}")
		if rev == 2:
			self.Lux1310SCIWrite(0x5B, 0x307f)
			self.Lux1310SCIWrite(0x7B, 0x3007)
		else:
			self.Lux1310SCIWrite(0x5B, 0x301f)
			self.Lux1310SCIWrite(0x7B, 0x3001)

		# Clear the ADC Offsets table, and then enable the ADC offset calibration. 
		for i in range(16):
			self.Lux1310Write(self.SCI.LUX1310_SCI_ADC_OS[i], 0);
		
		self.Lux1310Write(self.SCI.LUX1310_SCI_ADC_CAL_EN, 1);

		# Program the default gain and wavetable.*/
		self.Lux1310Write(self.SCI.LUX1310_SCI_GAIN_SEL_SAMP, 0x7f);
		self.Lux1310Write(self.SCI.LUX1310_SCI_GAIN_SEL_FB, 0x7f);
		self.Lux1310Write(self.SCI.LUX1310_SCI_GAIN_BIT, 3);
		#lux1310_write_wavetab(data, &lux1310_wt_sram80);
		# TODO: don't just assume the first wavetable is delay of 80!
		self.Lux1310WriteWaveTab(Lux1310WaveTables[0])

		#lux1310_set_gain(&data->sensor, 0, NULL);
		
		# Enable the sensor timing engine. */
		self.Lux1310Write(self.SCI.LUX1310_SCI_TIMING_EN, 1);
	


		#usleep(10000);
		time.sleep(0.01)
		self.mem.fpga_write32(IMAGER_FRAME_PERIOD, 100 * 4000)
		self.mem.fpga_write32(IMAGER_INT_TIME, 100 * 3900)
		#usleep(50000);
		time.sleep(0.05)


	#numfunc = lux1310num


	# def setDACCS(self, flag):
	# 	board_chronos14_gpio["lux1310-dac-cs"]
	# 	pass	

	# def WriteGPIO(name, value):
	# 	pass
	# 	#GPIOset

	def _htole16(self,bigend):
		return ((bigend & 0xff) << 8) | ((bigend & 0xff00) >> 8)

	def Lux1310SetVoltage(self, channel, mv, mul, div):
		vdac = int((LUX1310_DAC_FULL_SCALE * mv * mul) / (LUX1310_DAC_VREF * div))
		reg = self._htole16(((channel & 0x7) << 12) | vdac)
		self.mem.GPIOWrite("daccs", 0)
		spilist = [reg >> 8, reg & 255]
		#print (spilist)
		spi.transfer(spilist)

		self.mem.GPIOWrite("daccs", 1)

			
    # gpio_write(data->daccs, 0);
    # err = write(data->spifd, &reg, sizeof(reg));
    # gpio_write(data->daccs, 1);

	def _writeDACVoltage(self, chan, voltage):
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


	def _initDAC(self):
		spi.spi_open()
		spi.spi_transfer(0x9000)

	def _writeDACVoltages(self):
		self._initDAC();
		self._writeDACVoltage(VABL_VOLTAGE, 0.3);
		self._writeDACVoltage(VRSTB_VOLTAGE, 2.7);
		self._writeDACVoltage(VRST_VOLTAGE, 3.3);
		self._writeDACVoltage(VRSTL_VOLTAGE, 0.7);
		self._writeDACVoltage(VRSTH_VOLTAGE, 3.6);
		self._writeDACVoltage(VDR1_VOLTAGE, 2.5);
		self._writeDACVoltage(VDR2_VOLTAGE, 2);
		self._writeDACVoltage(VDR3_VOLTAGE, 1.5);






	def Lux1310Init(self):

		print ("Lux1310Init")

		self.mem.mm_open()
		#self.mem.initlux()

		#self.initDAC()
		self._writeDACVoltages()


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

		self.Lux1310AutoPhaseCal()







	def Lux1310AutoPhaseCal(self):
		pass