
from sensorobj import SensorObject
import spi
from lux1310h import *
from mmapregisters import *
import time
from dataclasses import dataclass
import struct

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



def Lux1310SetExposure():
	print ("Lux1310SetExposure")

def Lux1310SetPeriod():
	print ("Lux1310SetPeriod")

def Lux1310SetResolutions():
	pass

def Lux1310GetConstraints():
	pass

def Lux1310SetGain(gain):
	print ("Lux1310SetGain")
	for gdict in Lux1310GainData:
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




class Lux1310Object(SensorObject):

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
		readvalue = self.mem.fpga_mmio.read16(IMAGE_SENSOR_CONTROL_ADDR)
		if value:
			self.mem.fpga_mmio.write16(IMAGE_SENSOR_CONTROL_ADDR, readvalue | IMAGE_SENSOR_RESET_MASK)
		else:
			self.mem.fpga_mmio.write16(IMAGE_SENSOR_CONTROL_ADDR, readvalue & ~IMAGE_SENSOR_RESET_MASK)

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


