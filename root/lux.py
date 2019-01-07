import spi
from luxh import *

def setDACCS(flag):
	pass	




def writeDACVoltage(chan, voltage):
	if chan == VDR3_VOLTAGE:
		writeDAC(voltage * VDR3_SCALE, VDR3_VOLTAGE)
	elif chan == VABL_VOLTAGE:
		writeDAC(voltage * VABL_SCALE, VABL_VOLTAGE)
	elif chan == VDR1_VOLTAGE:
		writeDAC(voltage * VDR1_SCALE, VDR1_VOLTAGE)
	elif chan == VDR2_VOLTAGE:
		writeDAC(voltage * VDR2_SCALE, VDR2_VOLTAGE)
	elif chan == VRSTB_VOLTAGE:
		writeDAC(voltage * VRSTB_SCALE, VRSTB_VOLTAGE)
	elif chan == VRSTH_VOLTAGE:
		writeDAC(voltage * VRSTH_SCALE, VRSTH_VOLTAGE)
	elif chan == VRSTL_VOLTAGE:
		writeDAC(voltage * VRSTL_SCALE, VRSTL_VOLTAGE)
	elif chan == VRST_VOLTAGE:
		writeDAC(voltage * VRST_SCALE, VRST_VOLTAGE)
	else:
		pass


def writeDAC(data, channel):
	writeDACSPI(((int(channel) & 0x7) << 12) | (int(data) & 0x0FFF))


def writeDACSPI(data):
	spi.spi_transfer(data)


def writeDACVoltages():
	initDAC();
	writeDACVoltage(VABL_VOLTAGE, 0.3);
	writeDACVoltage(VRSTB_VOLTAGE, 2.7);
	writeDACVoltage(VRST_VOLTAGE, 3.3);
	writeDACVoltage(VRSTL_VOLTAGE, 0.7);
	writeDACVoltage(VRSTH_VOLTAGE, 3.6);
	writeDACVoltage(VDR1_VOLTAGE, 2.5);
	writeDACVoltage(VDR2_VOLTAGE, 2);
	writeDACVoltage(VDR3_VOLTAGE, 1.5);

def initDAC():
	spi.spi_open()
	spi.spi_transfer(0x9000)


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
