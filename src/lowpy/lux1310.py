from pprint import pprint
from termcolor import colored, cprint
import pdb
import math

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




NODAC = False
# NODAC = True


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

	# SPI * spi;
	# GPMC * gpmc;
	# UInt8 clkPhase;
	# Int16 offsetsA[16];


def within(x, mn, mx):
	if x > mx:
		return mx
	if x < mn:
		return mn
	return x


# Bit hacking to extract a value from a bitmask and shift it down.
def getbits(value, mask):
	# print (f"  ### getbits(0x{value:x}, 0x{mask:x})")
	if mask == 0:
		# print ("   ->0x0")
		return 0
	else:
		lsb = (~mask + 1) & mask
		# print (f"   ->0x{((value & mask) // lsb):x}")
		return (value & mask) // lsb


# Bit hacking to shift a value up to the position specified by the mask.
def setbits(value, mask):
	# print(f"Setbits ({value}, {mask}):")
	# print (f"  ### setbits(0x{value:x}, 0x{mask:x})")
	if mask == 0:
		# print ("   ->0x0")
		return 0
	else:
		lsb = (~mask + 1) & mask
		# print (f"   ->0x{((value * lsb) & mask):x}")
		return (value * lsb) & mask


class Lux1310Object(SensorObject):

	breakSCI = False
	# breakSCI = True

	noSCI = True
	noSCI = False

	# we'll keep a copy of the wavetable delay
	keepdelay = 0
	SCIc = 0  # how many SCI writes

	currentHRes = 1280
	currentVRes = 1024
	currentPeriod = 0
	currentExposure = 0

	#TODO: are all these used?
	masterMode = False
	masterModeTotalLines = 0
	dacCSFD = 0
	wavetableSize = 80
	gain = 0
	wavetableSelect = 0
	startDelaySensorClocks = LUX1310_MAGIC_ABN_DELAY
	sensorVersion = 0

	# get SCI constants
	SCI = SCIObject()

	thisSPIobj = spi.SPIobj()

	# SPI_DEV = "/dev/spidev3.0"
	# SPI_MODE = 1
	# SPI_SPEED = 1000000
	# SPI_BITORDER = "msb"
	# SPI_BITS = 16

	# spi = SPI(SPI_DEV, SPI_MODE, SPI_SPEED, SPI_BITORDER, SPI_BITS)

	# special LUX1310 variables


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
		{   # x2 - 6dB
			"vrstb": 2700,
			"vrst": 3300,
			"vrsth": 3600,
			"sampling": 0xfff,
			"feedback": 0x7f,
			"gain_bit": 3,
			"analog_gain": 6,
		},
		{    # x4 - 12dB
			"vrstb": 2700,
			"vrst": 3300,
			"vrsth": 3600,
			"sampling": 0xfff,
			"feedback": 0x7f,
			"gain_bit": 0,
			"analog_gain": 12,
		},
		{    # x8 - 18dB
			"vrstb": 1700,
			"vrst": 2300,
			"vrsth": 2600,
			"sampling": 0xfff,
			"feedback": 0x7,
			"gain_bit": 0,
			"analog_gain": 18,
		},
		{   # x16 - 24dB
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
		'''Write to the FPGA with an AND mask.'''
		readdata = self.mem.fpga_read16(addr)
		readdata &= mask
		self.mem.FPGAWrite16s(addr, readdata)
		# cprint (f"FPGAndBits: FPGAwrite16 - 0x{addr:x}: 0x{readdata:x}", "white", "on_blue")

	def FPGAOrBits(self, addr, mask):
		'''Write to the FPGA with an OR mask.'''
		readdata = self.mem.fpga_read16(addr)
		readdata |= mask
		self.mem.FPGAWrite16s(addr, readdata)
		# cprint (f"FPGAOrBits: FPGAwrite16 - 0x{addr:x}: 0x{readdata:x}", "white", "on_blue")

	def Lux1310SCIWriteWithMask(self, addr, value):
		'''ORIGINAL
		Perform a simple 16bit register write'''
		# NOTE: this uses the write + "s" methods, that do not print debug info
		if self.noSCI: return
		if self.breakSCI: breakpoint()

		self.mem.fpga_write16s(SENSOR_SCI_CONTROL, 0x8000)
		self.FPGAAndBits(SENSOR_SCI_CONTROL, 0xffff - SENSOR_SCI_CONTROL_RW_MASK)
		self.mem.fpga_write16s(SENSOR_SCI_ADDRESS, addr)
		self.mem.fpga_write16s(SENSOR_SCI_DATALEN, 2)
		self.mem.fpga_write8s(SENSOR_SCI_FIFO_WR_ADDR, (value >> 8) & 0xff)
		self.mem.fpga_write8s(SENSOR_SCI_FIFO_WR_ADDR, value & 0xff)

		# Start the transfer and then wait for completion.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

	def Lux1310SCIWritePure(self, addr, value):
		'''with pure writes instead of masked read-modify-write
		Perform a simple 16bit register write'''
		if self.noSCI: return
		if self.breakSCI: breakpoint()

		self.mem.fpga_write16(SENSOR_SCI_CONTROL, 0x8000)
		self.mem.fpga_write16(SENSOR_SCI_CONTROL, 0)
		self.mem.fpga_write16(SENSOR_SCI_ADDRESS, addr)
		self.mem.fpga_write16(SENSOR_SCI_DATALEN, 4)
		self.mem.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, (value >> 8) & 0xff)
		self.mem.fpga_write16(SENSOR_SCI_FIFO_WR_ADDR, value & 0xff)
	
		# Start the transfer and then wait for completion.
		self.mem.fpga_write16(SENSOR_SCI_CONTROL, 1)
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

	def Lux1310SCIWrite(self, addr, value):
		'''This is the main SCI write routine, using masked writes to certain bitfields'''
		if self.noSCI: return
		if self.breakSCI: breakpoint()
		self.Lux1310SCIWriteWithMask(addr, value)

	def Lux1310SCIWriteBuf(self, addr, values):
		'''Perform a series of 8 bit register writes'''
		# Clear RW, and setup the transfer and fill the FIFO
		debugWB = False
		if self.noSCI: return
		if self.breakSCI: breakpoint()

		# cprint (f"$$$ Lux1310SCIWriteBuf to 0x{addr:x}: {len(values)} entries", "white", "on_blue")
		rw = self.mem.fpga_read16(SENSOR_SCI_CONTROL) & (0xffff - SENSOR_SCI_CONTROL_RW_MASK)
		self.mem.FPGAWrite16(SENSOR_SCI_CONTROL, 0x8000 | rw)
		if debugWB:
			cprint (f"WB: fpga_write16s - 0x{SENSOR_SCI_CONTROL:x}: 0x{(0x8000 | rw):x}", "white", "on_blue")

		self.mem.FPGAWrite16(SENSOR_SCI_ADDRESS, addr)
		if debugWB:
			cprint (f"WB: fpga_write16s - 0x{SENSOR_SCI_ADDRESS:x}: 0x{addr:x}", "white", "on_blue")
		self.mem.FPGAWrite16(SENSOR_SCI_DATALEN, len(values))
		if debugWB:
			cprint (f"WB: fpga_write16s - 0x{SENSOR_SCI_DATALEN:x}: 0x{len(values):x}", "white", "on_blue")
		for b in values:
			self.mem.FPGAWrite16s(SENSOR_SCI_FIFO_WR_ADDR, b)
			if debugWB:
				# cprint (f"WB: fpga_write16s - 0x{SENSOR_SCI_FIFO_WR_ADDR:x}: 0x{b:x}", "white", "on_blue")
				print (b)
			# print (f"  - 0x{b:x}")

		# Start the transfer and then wait for completion.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		f = self.mem.fpga_read16(SENSOR_SCI_CONTROL)
		f = f & SENSOR_SCI_CONTROL_RUN_MASK
		# print (f"f is {f}")
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			# print (".")
			pass

	def Lux1310SCIRead(self, addr):
		'''Perform a simple 16bit register read'''
		# print(f" ### Lux1310SCIRead(0x{addr:x})")
		# Set RW, address and length.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RW_MASK)
		self.mem.fpga_write16s(SENSOR_SCI_ADDRESS, addr)
		self.mem.fpga_write16s(SENSOR_SCI_DATALEN, 2)
		
		# Start the transfer and then wait for completion.
		self.FPGAOrBits(SENSOR_SCI_CONTROL, SENSOR_SCI_CONTROL_RUN_MASK)
		while self.mem.fpga_read16(SENSOR_SCI_CONTROL) & SENSOR_SCI_CONTROL_RUN_MASK:
			pass

		return self.mem.fpga_read16(SENSOR_SCI_READ_DATA)
	
	def Lux1310Read(self, reg):
		# print(f"### Lux1310Read(0x{reg:x})")
		sciaddr = reg >> self.SCI.LUX1310_SCI_REG_ADDR
		val = self.Lux1310SCIRead(reg >> self.SCI.LUX1310_SCI_REG_ADDR)
		# print (f" ->0x{val:x}")
		return getbits(val, reg & self.SCI.LUX1310_SCI_REG_MASK)

	def Lux1310Write(self, reg, val):
		'''Perform a simple register write, which contains only one sub-field.
		NEW: pass a string instead
		'''

		#debug testing: sleep some
		# time.sleep(0.01)
		if self.noSCI: return
		if self.breakSCI: breakpoint()


		self.mem.writesCount += 1
		if type(reg) is str:
			lreg = Lux1310_dict[reg]
			sciaddr = lreg >> self.SCI.LUX1310_SCI_REG_ADDR
			scidata = setbits(val, lreg & self.SCI.LUX1310_SCI_REG_MASK)
			# cprint(f'  [{self.mem.writesCount}]$$$ Lux1310Write("{reg}", 0x{val:x}) - 0x{sciaddr:x}, 0x{scidata:x}', "yellow")
			self.Lux1310SCIWrite(sciaddr, scidata)
			# cprint(f"  SCI WRITE: 0x{sciaddr:x}: 0x{scidata:x}", "blue", "on_yellow")
		else:
			# cprint(f"  [{self.mem.writesCount}]$$$ Lux1310Write(0x{reg:x}, 0x{val:x})", "red")
			sciaddr = reg >> self.SCI.LUX1310_SCI_REG_ADDR
			scidata = setbits(val, reg & self.SCI.LUX1310_SCI_REG_MASK)
			self.Lux1310SCIWrite(sciaddr, scidata)
			# cprint(f"  SCI WRITE: 0x{sciaddr:x}: 0x{scidata:x}", "blue", "on_yellow")


	def Lux1310WriteWord(self, reg, val):
		'''Perform a full register write, without considering bit-field definitions
		NEW: pass a string instead
		'''
		if self.noSCI: return
		if self.breakSCI: breakpoint()

		self.mem.writesCount += 1
		if type(reg) is str:
			lreg = Lux1310_dict[reg]
			sciaddr = lreg >> self.SCI.LUX1310_SCI_REG_ADDR
			scidata = val
			# cprint(f'  [{self.mem.writesCount}]$$$ Lux1310WriteWord("{reg}", 0x{val:x}) - 0x{sciaddr:x}, 0x{scidata:x}', "yellow")
			self.Lux1310SCIWrite(sciaddr, scidata)
		else:
			# cprint(f'  [{self.mem.writesCount}]$$$ Lux1310WriteWord("{reg}", 0x{val:x}) - 0x{sciaddr:x}, 0x{scidata:x}', "yellow")
			sciaddr = reg >> self.SCI.LUX1310_SCI_REG_ADDR
			scidata = val
			self.Lux1310SCIWrite(sciaddr, scidata)

	def Lux1310ChangeCount(self, delta):
		self.SCIc = self.SCIc + delta

	def Lux1310WriteWaveTab(self, wavedict):
		print ("$$$ Lux1310WriteWaveTab")
		self.keepdelay = wavedict["read_delay"]
		waves = wavedict["table"]
		self.Lux1310Write("LUX1310_SCI_TIMING_EN", 0)
		delay =wavedict["read_delay"]
		self.Lux1310Write("LUX1310_SCI_RDOUT_DLY", delay)
		self.Lux1310Write("LUX1310_SCI_WAVETAB_SIZE", delay)
		self.Lux1310SCIWriteBuf(0x7F, waves);
		self.Lux1310Write("LUX1310_SCI_TIMING_EN", 1)


	def Lux1310MinPeriod(self, wavelen):
	
		t_hblank = 2
		t_tx = 25
		t_fovf = 50
		t_fovb = 50 # Duration between PRSTN falling and TXN falling (I think) 
		
		g = self.ImageGeometry
		# Sum up the minimum number of clocks to read a frame at this resolution 
		t_read = (g.hres / LUX1310_HRES_INCREMENT)
		t_row = max(t_read + t_hblank, wavelen + 3)
		# print (f"comparing {t_read + t_hblank} and {wavelen + 3}")
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
		# print (f" t_frame = {t_frame}")
		
		self.mem.fpga_write32(IMAGER_FRAME_PERIOD, int(t_frame))
		for i in Lux1310WaveTables:
			# if t_frame >= self.lux1310_min_period(i[""])
			#print (i["read_delay"])
			min_period = self.Lux1310MinPeriod(i["read_delay"])
			# print (f"{i['read_delay']}: min period is {min_period}")
			if t_frame >= min_period:
				self.Lux1310WriteWaveTab(i)
				break
		
	def Lux1310GetMinFramePeriod(self, hRes, vRes, wtSize = LUX1310_MIN_WAVETABLE_SIZE):
		if not self.Lux1310IsValidResolution(hRes, vRes, 0, 0):
			return 0
		if(hRes == 1280):
			wtSize = 80
		tRead = (hRes / LUX1310_HRES_INCREMENT) * LUX1310_CLOCK_PERIOD
		tHBlank = 2 * LUX1310_CLOCK_PERIOD
		tWavetable = wtSize * LUX1310_CLOCK_PERIOD
		tRow = max(tRead+tHBlank, tWavetable+3*LUX1310_CLOCK_PERIOD)
		tTx = 25 * LUX1310_CLOCK_PERIOD
		tFovf = 50 * LUX1310_CLOCK_PERIOD
		#TODO: why are these the same
		tFovb = (50) * LUX1310_CLOCK_PERIOD #Duration between PRSTN falling and TXN falling (I think)
		tFrame = tRow * vRes + tTx + tFovf + tFovb
		print (f"getMinFramePeriod: {tFrame}")
		return math.ceil(tFrame * 100000000.0)

	def Lux1310GetIntegrationTime(self):
		return self.currentExposure / 100000000.0

	def Lux1310SetResolutions(self):
		print ("### Lux1310SetResolutions")
		g = self.ImageGeometry
		h_start = int(g.hoffset / LUX1310_HRES_INCREMENT)
		h_width = int(g.hres / LUX1310_HRES_INCREMENT)
		# print (h_start)
		# print (h_width)
		self.Lux1310Write("LUX1310_SCI_X_START", LUX1310_BLACK_COLS + h_start * LUX1310_HRES_INCREMENT);
		self.Lux1310Write("LUX1310_SCI_X_END", LUX1310_BLACK_COLS + (h_start + h_width) * LUX1310_HRES_INCREMENT - 1)
		self.Lux1310Write("LUX1310_SCI_Y_START", g.voffset)
		self.Lux1310Write("LUX1310_SCI_Y_END", g.voffset + g.vres - 1)
		return 0
		


	def Lux1310GetMinMasterFramePeriod(self, hRes, vRes):
		if not self.Lux1310IsValidResolution(hRes, vRes, 0, 0):
			return 0.0

		return self.Lux1310GetMinFramePeriod(hRes, vRes) / 100000000.0
		
		''' this was in camApp after the "return"
		int wtSize;

		if(hRes == 1280)
			wtSize = 80;
		else
			wtSize = LUX1310_MIN_WAVETABLE_SIZE;

		double tRead = (double)(hRes / LUX1310_HRES_INCREMENT) * LUX1310_CLOCK_PERIOD;
		double tHBlank = 2.0 * LUX1310_CLOCK_PERIOD;
		double tWavetable = wtSize * LUX1310_CLOCK_PERIOD;
		double tRow = max(tRead+tHBlank, tWavetable+3*LUX1310_CLOCK_PERIOD);
		double tTx = 25 * LUX1310_CLOCK_PERIOD;
		double tFovf = 50 * LUX1310_CLOCK_PERIOD;
		double tFovb = (50) * LUX1310_CLOCK_PERIOD;//Duration between PRSTN falling and TXN falling (I think)
		double tFrame = tRow * vRes + tTx + tFovf + tFovb;
		qDebug() << "getMinMasterFramePeriod:" << tFrame;
		return tFrame;
		'''
	
	def Lux1310SetSlavePeriod(self, period):
		self.mem.FPGAWrite32("IMAGER_FRAME_PERIOD", period)

	def Lux1310SetSlaveExposure(self, exposure):
		#hack to fix line issue. Not perfect, need to properly register this on the sensor clock.
		linePeriod = max((self.currentHRes / LUX1310_HRES_INCREMENT) + 2, (self.wavetableSize + 3)) * 1.0/LUX1310_SENSOR_CLOCK	#Line period in seconds
		startDelay = int(self.startDelaySensorClocks * TIMING_CLOCK_FREQ / LUX1310_SENSOR_CLOCK)
		targetExp = exposure / 100000000.0
		expLines = round(targetExp / linePeriod)

		newexposure = int(startDelay + (linePeriod * expLines * 100000000.0))
		#qDebug() << "linePeriod" << linePeriod << "startDelaySensorClocks" << startDelaySensorClocks << "startDelay" << startDelay
		#		 << "targetExp" << targetExp << "expLines" << expLines << "exposure" << exposure;
		self.mem.FPGAWrite32("IMAGER_INT_TIME", newexposure)
		self.currentExposure = newexposure



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
		return
		if NODAC:
			return
		print (f"Lux1310SetGain: {gain}")
		for gdict in self.Lux1310GainData:
			if gdict["analog_gain"] == gain:
				self.Lux1310SetVoltage(VRSTB_VOLTAGE, gdict["vrstb"], 1, 1)
				self.Lux1310SetVoltage(VRST_VOLTAGE, gdict["vrst"], LUX1310_VRST_MUL, LUX1310_VRST_DIV)
				#NOTE: this uses LUX1310_VRST_DIV in camm-daemon:
				self.Lux1310SetVoltage(VRSTH_VOLTAGE, gdict["vrsth"], LUX1310_VRST_MUL, LUX1310_VRSTH_DIV)


				self.Lux1310Write("LUX1310_SCI_GAIN_SEL_SAMP", gdict["sampling"])
				self.Lux1310Write("LUX1310_SCI_GAIN_SEL_FB", gdict["feedback"])
				self.Lux1310Write("LUX1310_SCI_GAIN_BIT", gdict["gain_bit"])

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


				# for j in range(LUX1310_ADC_COUNT):
				#for j in range(self.adc_count):
					# self.Lux1310Write(self.SCI.LUX1310_SCI_ADC_OS[j], 0)
				# for (j = 0; j < sensor->adc_count; j++) {
				#     uint16_t x = abs(caldata[j]) & ((1 << LUX1310_ADC_OFFSET_BITS) - 1);
				#     if (caldata[j]) x |= (1 << LUX1310_ADC_OFFSET_BITS);
				#     lux1310_write(data, LUX1310_SCI_ADC_OS(j), x);

				
				break
		pass

	def Lux1310GetMaxExposure(self, period):
		return period - 500


	def Lux1310GetActualFramePeriod(self, targetPeriod, hRes, vRes):
		#Round to nearest 10ns period
		targetPeriod = round(targetPeriod * (100000000.0)) / 100000000.0

		minPeriod = self.Lux1310GetMinMasterFramePeriod(hRes, vRes)
		maxPeriod = LUX1310_MAX_SLAVE_PERIOD

		return within(targetPeriod, minPeriod, maxPeriod);



	def Lux1310SetIntegrationTime(self, intTime, hRes, vRes):
		#Round to nearest 10ns period
		intTime = round(intTime * (100000000.0)) / 100000000.0

		#Set integration time to within limits
		maxIntTime = self.Lux1310GetMaxExposure(self.currentPeriod) / 100000000.0
		minIntTime = LUX1310_MIN_INT_TIME
		intTime = within(intTime, minIntTime, maxIntTime)
		self.currentExposure = intTime * 100000000.0
		self.Lux1310SetSlaveExposure(self.currentExposure)
		return intTime;



	def Lux1310SetFramePeriod(self, period, hRes, vRes):
		#Round to nearest 10ns period
		# breakpoint()
		period = round(period * (100000000.0)) / 100000000.0
		print (f"Requested period {period}")
		minPeriod = self.Lux1310GetMinMasterFramePeriod(hRes, vRes)
		maxPeriod = LUX1310_MAX_SLAVE_PERIOD / 100000000.0

		period = within(period, minPeriod, maxPeriod)
		self.currentPeriod = int(period * 100000000.0)
		self.Lux1310SetSlavePeriod(self.currentPeriod)
		return period;

	def Lux1310UpdateWavetableSetting(self):

		if self.wavetableSelect == LUX1310_WAVETABLE_AUTO:
			print (f"currentPeriod is {currentPeriod}, min period is {getMinFramePeriod(currentHRes, currentVRes, 80)}")
			if self.currentPeriod < self.Lux1310GetMinFramePeriod(currentHRes, currentVRes, 80):
				if self.currentPeriod < self.Lux1310GetMinFramePeriod(currentHRes, currentVRes, 39):
					if self.currentPeriod < self.Lux1310GetMinFramePeriod(currentHRes, currentVRes, 30):
						if self.currentPeriod < self.Lux1310GetMinFramePeriod(currentHRes, currentVRes, 25):
							self.Lux1310SetWavetable(LUX1310_WAVETABLE_20)
						else:
							self.Lux1310SetWavetable(LUX1310_WAVETABLE_25)
					else:
						self.Lux1310SetWavetable(LUX1310_WAVETABLE_30)
				else:
					self.Lux1310SetWavetable(LUX1310_WAVETABLE_39)			
			else:
				self.Lux1310SetWavetable(LUX1310_WAVETABLE_80)
		else:
			self.Lux1310SetWavetable(self.wavetableSelect)




	def Lux1310CalGain(self):
		pass

	def Lux1310CalSuffix(self):
		pass


	def Lux1310IsValidResolution(self, hRes, vRes, hOffset, vOffset):
		# Enforce resolution limits. 
		if (hRes < LUX1310_MIN_HRES) or (hRes + hOffset > LUX1310_MAX_H_RES):
			return False
		
		if (vRes < LUX1310_MIN_VRES) or (vRes + vOffset > LUX1310_MAX_V_RES):
			return False

		# Enforce minimum pixel increments. 
		if (hRes % LUX1310_HRES_INCREMENT) or (hOffset % LUX1310_HRES_INCREMENT):
			return False

		if (vRes % LUX1310_VRES_INCREMENT) or (vOffset % LUX1310_VRES_INCREMENT):
			return False
		
		# Otherwise, the resultion and offset are valid. 
		return True
	



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
		cprint ("### lux1310 __init__", "red", "on_white")
		# print (f"mem is {mem}")
		SensorObject.__init__(self, mem)

	def Lux1310RegDump(self):
		cprint ("Lux1310 Register Dump", "blue")
		for reg, val in Lux1310_dict.items():
			cont = self.Lux1310SCIRead(val >> 16)
			cprint (f"--> {reg:<35} (0x{val >> 16:x}) : 0x{(cont):x}", "blue")


	def LuxInit2(self):
		'''these things are moved to later'''

		# self.Lux1310RegDump()

		print ("LuxInit2")
		# Grab the sensor revision for further tuning.
		rev = self.Lux1310Read(self.SCI.LUX1310_SCI_REV_CHIP) 
		#rev = self.Lux1310Read("LUX1310_SCI_REV_CHIP") & 0xff
		print(f"configuring for LUX1310 silicon rev {rev}")
		if rev == 2:
			#self.Lux1310SCIWrite(0x5B, 0x307f)
			self.Lux1310WriteWord("LUX1310_SCI_TERMB_RXCLK", 0x307f)
			self.Lux1310SCIWrite(0x7B, 0x3007) #TODO this is an undocumented register!
			# print ("< undocumented 0x7b Lux write >")
		else:
			# self.Lux1310SCIWrite(0x5B, 0x301f)
			# self.Lux1310SCIWrite(0x7B, 0x3001)
			self.Lux1310WriteWord("LUX1310_SCI_TERMB_RXCLK", 0x301f)
			self.Lux1310SCIWrite(0x7B, 0x3001) #TODO this is an undocumented register!
			# print ("< undocumented 0x7b Lux write >")

		#TODOfix later:
		self.Lux1310ChangeCount(1) #because of 

		# Clear the ADC Offsets table, and then enable the ADC offset calibration. 
		for i in range(16):
			self.Lux1310Write(self.SCI.LUX1310_SCI_ADC_OS[i], 0);
			#TEST:
			# self.Lux1310Write(self.SCI.LUX1310_SCI_ADC_OS[i], i);
			# print (f"SCI WRITE {i}")


		self.Lux1310Write("LUX1310_SCI_ADC_CAL_EN", 1);

		#also TODO: loadADCOffsetsFromFile()
		
		# Program the default gain and wavetable.*/
		self.Lux1310Write("LUX1310_SCI_GAIN_SEL_SAMP", 0x7f);
		self.Lux1310Write("LUX1310_SCI_GAIN_SEL_FB", 0x7f);
		self.Lux1310Write("LUX1310_SCI_GAIN_BIT", 3);			#(38)
		#lux1310_write_wavetab(data, &lux1310_wt_sram80);
		# TODO: don't just assume the first wavetable is delay of 80!
	
		# while True:
		self.Lux1310SCIWriteBuf(0x7F, Lux1310Wave80Data);
			# time.sleep(0.1)
		# self.Lux1310SCIWriteBuf(0x7F, Lux1310Wave80Data);
		
		self.Lux1310Write("LUX1310_SCI_TIMING_EN", 1);
		
		time.sleep(0.01)
		self.mem.FPGAWrite32("IMAGER_FRAME_PERIOD", 100 * 4000)
		self.mem.FPGAWrite32("IMAGER_INT_TIME", 100 * 3900)
		time.sleep(0.05)
	

		self.currentHRes = 1280
		self.currentVRes = 1024
		self.Lux1310SetFramePeriod(self.Lux1310GetMinFramePeriod(self.currentHRes, self.currentVRes)/100000000.0, self.currentHRes, self.currentVRes)
		#mem problem before this
		self.Lux1310SetIntegrationTime(self.Lux1310GetMaxExposure(self.currentPeriod) / 100000000.0, self.currentHRes, self.currentVRes)

		print ("done LuxInit2")


	def _htole16(self,bigend):
		return ((bigend & 0xff) << 8) | ((bigend & 0xff00) >> 8)

	def Lux1310SetVoltage(self, channel, mv, mul, div):
		vdac = int((LUX1310_DAC_FULL_SCALE * mv * mul) / (LUX1310_DAC_VREF * div))
		reg = self._htole16(((channel & 0x7) << 12) | vdac)
		self.mem.GPIOWrite("lux1310-dac-cs", 0)
		self.thisSPIobj.spi_transfer3(reg)
		self.mem.GPIOWrite("lux1310-dac-cs", 1)

	def _writeDACVoltage(self, chan, voltage):
		# cprint(f"_writeDACVoltage: {chan}, {voltage}V", "blue", "on_white")
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


	def writeDAC(self, fdata, channel):
		data = int(fdata)
		# cprint(f"   writeDAC {channel}: 0x{data:x}", "blue", "on_white")
		self.writeDACSPI(((int(channel) & 0x7) << 12) | (int(data) & 0x0FFF))


	def writeDACSPI(self, data):
		# cprint(f"      writeDACSPI 0x{data:x}", "blue", "on_white")
		self.mem.GPIOWrite("lux1310-dac-cs", 0)	
		self.thisSPIobj.spi_transfer3(data)
		self.mem.GPIOWrite("lux1310-dac-cs", 1)
		


	def _initDAC(self):
		# spi.spi_open()
		self.thisSPIobj.spi_open3()
		cprint(f" initDAC:     writeDACSPI 0x{0x9000:x}", "blue", "on_white")
		self.mem.GPIOWrite("lux1310-dac-cs", 0)
		self.thisSPIobj.spi_transfer3(0x9000)	
		self.mem.GPIOWrite("lux1310-dac-cs", 1)
		
	def _blinkCS(self):
		while True:
			print ("Blinking DAC CS")
			self.mem.GPIOWrite("record-led.0", 0)
			self.mem.GPIOWrite("record-led.1", 0)
			self.mem.GPIOWrite("lux1310-dac-cs", 0)
			time.sleep(1)
			print ("...")
			self.mem.GPIOWrite("record-led.0", 1)
			self.mem.GPIOWrite("record-led.1", 1)
			self.mem.GPIOWrite("lux1310-dac-cs", 1)
			time.sleep(1)
		
	def SPITransfer16(self, data):
		print (f"SPITransfer16: 0x{data:x}")
		tup = [(data >> 8) & 0xff, data & 0xff]
		spiobj.transfer(tup)

	def testSPI(self):

		self.thisSPIobj.spi_open3()
		n = 0
		while True:
			cprint(f" SPI TEST{n}", "blue", "on_white")
			self.mem.GPIOWrite("lux1310-dac-cs", 0)

			self.thisSPIobj.spi_transfer3(0x9123)	

			self.mem.GPIOWrite("lux1310-dac-cs", 1)
			# time.sleep(0.1)
			n += 1



	def _writeDACVoltages(self):	
		# breakpoint()
		print("_writeDACVoltages")
		self._initDAC()
		self._writeDACVoltage(VABL_VOLTAGE, 0.3);
		self._writeDACVoltage(VRSTB_VOLTAGE, 2.7);
		self._writeDACVoltage(VRST_VOLTAGE, 3.3);
		self._writeDACVoltage(VRSTL_VOLTAGE, 0.7);
		self._writeDACVoltage(VRSTH_VOLTAGE, 3.6);
		self._writeDACVoltage(VDR1_VOLTAGE, 2.5);
		self._writeDACVoltage(VDR2_VOLTAGE, 2);
		self._writeDACVoltage(VDR3_VOLTAGE, 1.5);


	def Lux1310SetWavetable(self, mode):
		self.Lux1310Write("LUX1310_SCI_TIMING_EN", 0x8000) # Disable internal timing engine
		self.Lux1310Write("LUX1310_SCI_RDOUT_DLY", Lux1310Wavetables[mode]["read_delay"]) # non-overlapping readout delay
		self.Lux1310Write("LUX1310_SCI_WAVETAB_SIZE", Lux1310Wavetables[mode]["read_delay"]) # wavetable size
		self.Lux1310SCIWriteBuf(0x7f, Lux1310Wavetables[mode]["table"]) # Enable internal timing engine
		self.Lux1310Write("LUX1310_SCI_TIMING_EN", 0x0001)
		self.wavetableSize = Lux1310Wavetables[mode]["read_delay"]
		self.Lux1310SetABNDelayClocks(Lux1310Wavetables[mode]["read_delay"])
		
		print (f"Wavetable size set to {self.wavetableSize}")


	def Lux1310SetABNDelayClocks(self, ABNOffset):
		self.mem.FPGAWrite16("SENSOR_MAGIC_START_DELAY", ABNOffset)

	# def Lux1310Init2(self):
	# 	# Now do rest of lux init

	# 	self.Lux1310AutoPhaseCal()

	# 	self.Lux1310Write("LUX1310_SCI_GAIN_SEL_SAMP", 0x7f);

	# def Lux1310Init(self):

	# 	print ("Lux1310Init")





		# Set up DAC with SPI
	def lux1310SetReset(self, value):
		readvalue = self.mem.fpga_mmio.read16(IMAGE_SENSOR_CONTROL)
		if value:
			self.mem.FPGAWrite16(IMAGE_SENSOR_CONTROL, readvalue | IMAGE_SENSOR_RESET_MASK)
		else:
			self.mem.FPGAWrite16(IMAGE_SENSOR_CONTROL, readvalue & 0xffff - IMAGE_SENSOR_RESET_MASK)

	def SensorInit(self):
		print ("SensorInit")

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


	def Lux1310WriteSCITest(self):
		#print ("### Lux1310WriteSCITest")

		# cprint (" read test", "blue")
		# crev = self.Lux1310Read(self.SCI.LUX1310_SCI_REV_CHIP)
		# cid = self.Lux1310Read(self.SCI.LUX1310_SCI_CHIP_ID)
		# cprint (f"  rev: 0x{crev:x}", "blue")
		# cprint (f"  id: 0x{cid:x}", "blue")

		cprint (" write test", "blue")
		xend = self.Lux1310Read(self.SCI.LUX1310_SCI_SEL_VDR2_WIDTH)
		cprint (f"  vdr2 width: 0x{xend:x}", "blue")
		self.Lux1310Write(self.SCI.LUX1310_SCI_SEL_VDR2_WIDTH, 0xabcd)
		xend = self.Lux1310Read(self.SCI.LUX1310_SCI_SEL_VDR2_WIDTH)
		cprint (f"  vdr2 width now: 0x{xend:x}\n", "blue")




	def Lux1310AutoPhaseCal(self):
		# breakpoint()

		pass

	def Lux1310GetDataCorrect(self):
		return self.mem.FPGARead32("SENSOR_DATA_CORRECT")


	def SensorInit2(self):
		#print ("-------------------------\n### Lux1310AutoPhaseCal")

		# breakpoint()

		self.Lux1310WriteWord("LUX1310_SCI_CUST_PAT", 0xfc0)
		# check = self.Lux1310Read(self.SCI.LUX1310_SCI_CUST_PAT)
		# print (f"  check is {check:x}")
		self.Lux1310Write("LUX1310_SCI_TST_PAT", 2)
		self.Lux1310Write("LUX1310_SCI_PCLK_VBLANK", 0xfc0)
		
		#pdb.set_trace()
		self.Lux1310WriteWord("LUX1310_SCI_DAC_ILV", 0xe1)

		#clock phase moved to here
		self.Lux1310AutoPhaseCal()
		
		# Toggle the clock phase and wait for the FPGA to lock. 
		self.mem.FPGAWrite16(SENSOR_CLK_PHASE, 0)
		self.mem.FPGAWrite16(SENSOR_CLK_PHASE, 1)
		self.mem.FPGAWrite16(SENSOR_CLK_PHASE, 0)
		#/ TODO: Shouldn't there be a while loop here? */
		data_correct = self.Lux1310GetDataCorrect()
		print(f"\nlux1310_data_correct: {data_correct}")

		self.Lux1310Write("LUX1310_SCI_PCLK_VBLANK", 0xf00)
		self.Lux1310Write("LUX1310_SCI_TST_PAT", 0x0)  # ADC clock control

		self.Lux1310Write("LUX1310_SCI_RDOUT_DLY", 80)
		self.Lux1310Write("LUX1310_SCI_WAVETAB_SIZE", 80)
		self.Lux1310Write("LUX1310_SCI_LINE_VALID_DLY", 7)
		self.Lux1310Write("LUX1310_SCI_STATE_IDLE_CTRL0", 0xe08e)
		self.Lux1310Write("LUX1310_SCI_STATE_IDLE_CTRL1", 0xfc1f)
		self.Lux1310Write("LUX1310_SCI_STATE_IDLE_CTRL2", 0x0003)
		
		self.Lux1310Write("LUX1310_SCI_ADC_CLOCK_CTRL", 0x2202)
		#self.Lux1310Write("LUX1310_SCI_SEL_VCMI", 6)
		#self.Lux1310Write("LUX1310_SCI_SEL_VCMO", 7)
		#self.Lux1310Write("LUX1310_SCI_SEL_VCMP", 11)
		#self.Lux1310Write("LUX1310_SCI_SEL_VCMN", 4)
		#this replaces the above four writes:
		self.Lux1310Write("LUX1310_SCI_SEL_VCM", 0x4b76)
		self.Lux1310Write("LUX1310_SCI_INT_CLK_TIMING", 0x41f);

		#rev = self.Lux1310Read("LUX1310_SCI_REV_CHIP")
		#print (f"Found revision {rev}")

		return

		# we don't do the following

		self.Lux1310Write("LUX1310_SCI_INT_CLK_TIMING", 0x41f);

		self.Lux1310Write("LUX1310_SCI_MSB_FIRST_DATA", 0)
		self.Lux1310Write("LUX1310_SCI_TERMB_CLK", 1)
		self.Lux1310Write("LUX1310_SCI_TERMB_DATA", 1)
		self.Lux1310Write("LUX1310_SCI_DCLK_INV", 1)
		self.Lux1310Write("LUX1310_SCI_PCLK_INV", 0)

		# Return to normal mode. 
		self.Lux1310Write("LUX1310_SCI_PCLK_VBLANK", 0xf00)
		self.Lux1310Write("LUX1310_SCI_TST_PAT", 0)


		pass


		
	# def InitSensor():
	# 	# UGH.... now doing this in the proper place

	# 	self.wavetableSize = 80
	# 	self.gain = LUX1310_GAIN_1


	def Lux1310WriteDGCMem(self, gain, column):
		self.mem.FPGAWrite16(DCG_MEM_START_ADDR + 2 * column, gain * 4096.0)


	def Lux1310LoadColGainFromFile(self):

		#TODO: actual file reading
		# right now this sets gain of 1.0
		# breakpoint()
		if(True):
			print("Resetting cal gain to 1.0")
			for i in range(16):
				#self.gainCorrection[i] = 1.0
				pass
		
		
		# Write the values into the display column gain memory
		DCGstart = 0x1000
		for i in range(LUX1310_MAX_H_RES):
			gain = 1.0
			self.mem.fpga_write16s(DCGstart + 2 * (i ), int(gain * 4096.0))
			#self.Lux1310WriteDGCMem(gainCorrection[i % 16], i);

	def Lux1310ZeroFPNArea(self):
		FRAME_SIZE = 1280 * 1024 * 12 // 8

		print ( "Zero FPN area")

		return
		self.mem.FPGAWrite32("GPMC_PAGE_OFFSET", 0)	# Set GPMC offset
		for i in range(0, FRAME_SIZE, 2):
			self.mem.RAMWrite16(i, 0)
			# if not (i & 0x3ff): print (f"0x{i:x}")

	def Lux1310PrintFPNArea(self):
		FRAME_SIZE = 1280 * 1024 * 12 // 8

		print ( "Contents of FPN area")
		self.mem.FPGAWrite32("GPMC_PAGE_OFFSET", 0)	# Set GPMC offset
		for i in range(0, FRAME_SIZE, 2):
			fpn = elf.mem.ReadWrite16(i, 0)
			if not (i & 0xff): print (f"0x{i:x}: 0x{fpn:x}")



	def Lux1310ShowTestPattern(self):
		print ("Showing test pattern")

		# breakpoint()

		FRAME_SIZE = 1280 * 1024 * 12 // 8

		print ("Setting display addresses")
		cr = self.mem.FPGARead16("DISPLAY_CTL") | 1	
		self.mem.FPGAWrite16nb("DISPLAY_CTL", cr) #Set to display from display frame address register
		self.mem.FPGAWrite32nb("DISPLAY_FRAME_ADDRESS", 0x40000)	# Set display address


		print ("Testing RAM R/W")
		x = self.mem.RAMRead8(0)
		print (f" - reading {x}")
		print (" - writing...")
		self.mem.RAMWrite8(0, 123)
		x = self.mem.RAMRead8(0)
		print (f" - reading {x}")
		



		print ( "Zero FPN area")
		# breakpoint()
		self.mem.FPGAWrite32("GPMC_PAGE_OFFSET", 0)	# Set GPMC offset
		for i in range(0, FRAME_SIZE, 2):
			self.mem.RAMWrite16(i, 0)
			if not (i & 0xff): print (f"0x{i:x}")


		
		print ("Zero image area")
		#Zero image area
		self.mem.FPGAWrite32nb("GPMC_PAGE_OFFSET", 0x40000) #Set GPMC offset
		for i in range(0, FRAME_SIZE, 2):
			# self.mem.RAMWrite16(i, (i >> 8) & 0xff80)
			self.mem.RAMWrite16(i, (i >> 8) & 0xff80)

		print ("Draw a rectangular box with diagonal")
		# Draw a rectangular box around the outside of the screen and a diagonal lines starting from the top left
		#for(int i = 0; i < 1; i++)
		#{
		
		# breakpoint()

		for y in range(80): 
			for x in range(128):	
			
				# self.writePixel12(x+y*1280, 0x2000000, 2048) #(x == 0 || y == 0 || x == 1279 || y == 1023 || x == y) ? 0xFFF : 0);
				d =  ((x == 0) or (y == 0) or (x == 1279) or (y == 1023) or (x == y)) 
				if d:
					self.writePixel12(x+y*1280, 0x0000000, 0xFFF )
				else:
					self.writePixel12(x+y*1280, 0x0000000, 0)
				# self.writePixel12(x+y*1280, 0x2000000, ((x == 0) || (y == 0) || (x == 1279) || (y == 1023) || (x == y)) ? 0xFFF : 0);
				# self.writePixel12(x+y*1280, 0x2000000,  (x == y) ? 0xFFF : 0);
				#print(".")
				#qDebug() << "line" << y;
				pass

		print ("Set GPMC offset")
		self.mem.FPGAWrite32("GPMC_PAGE_OFFSET", 0) # Set GPMC offset
		print ("done")


	def writePixel12(self, pixel, offset, value):
		address = pixel * 12 // 8 + offset
		shift = (pixel & 0x1) * 4
		dataL = self.mem.RAMRead8(address)
		dataH = self.mem.RAMRead8(address+1)

		maskL = 0xff - (0xFF << shift)
		maskH = 0xff - (0xFFF >> (8 - shift))
		dataL &= maskL
		dataH &= maskH

		dataL |= (value << shift)
		dataH |= (value >> (8 - shift))
		self.mem.RAMWrite8(address, dataL)
		self.mem.RAMWrite8(address+1, dataH)
