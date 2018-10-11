"""
Module for communicating with the power controller. It runs on a timer, and updates the
batt* variables sent by the power controller



"""

import	time, serial

# Set up serial port for power controller

PWRCMD_SOF_VALUE =          0x5a

PWRCMD_GET_DATA =           0x00
PWRCMD_SHUTDOWN =           0x01
PWRCMD_REQ_POWERDOWN =      0x02
PWRCMD_JUMP_BOOTLOADER =    0x03
PWRCMD_GET_DATA_EXT =       0x04

PWRCMD_IS_IN_BOOTLOADER =   0x7f

# Flags for the extended battery data. 
PWRCMD_FLAG_BATT_PRESENT =  0x01
PWRCMD_FLAG_LINE_POWER =    0x02
PWRCMD_FLAG_CHARGING  =     0x04

CAM_PWRCTRL_BAUDRATE =      57600



ser = serial.Serial('/dev/ttyO0')
#ser = serial.Serial('/dev/pts/4')


def DoSendSerial():

	#it has to be done in this order!
	OpenSerial()
	
	# send command to return battery information; it will be ready by next DoSerial()
	pwrcmd_command(PWRCMD_GET_DATA_EXT)

def DoReceiveSerial():

	#try to read data first	
	ReadSerial()

def OpenSerial():
	ser = serial.Serial('/dev/ttyO0', CAM_PWRCTRL_BAUDRATE)  # open serial port

packnum = 0;
def ReadSerial():

	global packnum
	packnum = packnum + 1;
	siw = ser.in_waiting

	MAXREAD = 40
	
	dlist = []


	if siw > 3:

		dataAvailable = True
		while dataAvailable:
			packetDataReady = True
			dlen = -1;
			while packetDataReady:
				#print ("\n------- packet", packnum, "-------")
				#print ("siw is", siw)

				for i in range(siw):
				 
					ch = ser.read()
					if i == 2:
						dlen = ord(ch)
						#print ("length is", dlen)
					dlist.append(ord(ch))
					if i == dlen + 4 or i >= MAXREAD:
						packetDataReady = False
						break





			#print (dlist)
			if not CheckCRC(dlist):
				print ("CRC fail on incoming data") 
		
			command = dlist[3]
			if command == PWRCMD_REQ_POWERDOWN:
				print ("Shutdown request!")
			elif command == PWRCMD_GET_DATA_EXT:
				ParseBatteryData(dlist)

			#check if this is the last packet
			if dlen + 5 == siw:
				#print ("no more packets!")
				dataAvailable = False

			siw = siw - dlen - 5
			dlist = []



		return

def ParseBatteryData(dlist):

	#now set power variables
	battCapacityPercent = dlist[4]
	battSOHPercent = dlist[5]
	battVoltage = dlist[6] << 8 | dlist[7]
	battCurrent = dlist[8] << 8 | dlist[9]
	battHiResCap = dlist[10] << 8 | dlist[11]
	battHiResSOC = dlist[12] << 8 | dlist[13]

	if len(dlist) >= 19:
		battVoltageCam = dlist[14] << 8 | dlist[15]
		battCurrentCam = dlist[16] << 8 | dlist[17]
		battmbTemperature = dlist[18] << 8 | dlist[19]
		battflags = dlist[20]
		battfanPWM = dlist[21]

	'''
	print ("battCapacityPercent =", battCapacityPercent)
	print ("battSOHPercent =", battSOHPercent)
	print ("battVoltage =", battVoltage)
	print ("battCurrent =", battCurrent)
	print ("battHiResCap =", battHiResCap)
	print ("battHiResSOC =", battHiResSOC)
	print ("battVoltageCam =", battVoltageCam)
	print ("battCurrentCam =", battCurrentCam)
	print ("mbTemperature =", battmbTemperature)
	print ("flags =", battflags)
	print ("fanPWM =", battfanPWM)
	'''


wCRCTable = [
	0X0000, 0XC0C1, 0XC181, 0X0140, 0XC301, 0X03C0, 0X0280, 0XC241,
	0XC601, 0X06C0, 0X0780, 0XC741, 0X0500, 0XC5C1, 0XC481, 0X0440,
	0XCC01, 0X0CC0, 0X0D80, 0XCD41, 0X0F00, 0XCFC1, 0XCE81, 0X0E40,
	0X0A00, 0XCAC1, 0XCB81, 0X0B40, 0XC901, 0X09C0, 0X0880, 0XC841,
	0XD801, 0X18C0, 0X1980, 0XD941, 0X1B00, 0XDBC1, 0XDA81, 0X1A40,
	0X1E00, 0XDEC1, 0XDF81, 0X1F40, 0XDD01, 0X1DC0, 0X1C80, 0XDC41,
	0X1400, 0XD4C1, 0XD581, 0X1540, 0XD701, 0X17C0, 0X1680, 0XD641,
	0XD201, 0X12C0, 0X1380, 0XD341, 0X1100, 0XD1C1, 0XD081, 0X1040,
	0XF001, 0X30C0, 0X3180, 0XF141, 0X3300, 0XF3C1, 0XF281, 0X3240,
	0X3600, 0XF6C1, 0XF781, 0X3740, 0XF501, 0X35C0, 0X3480, 0XF441,
	0X3C00, 0XFCC1, 0XFD81, 0X3D40, 0XFF01, 0X3FC0, 0X3E80, 0XFE41,
	0XFA01, 0X3AC0, 0X3B80, 0XFB41, 0X3900, 0XF9C1, 0XF881, 0X3840,
	0X2800, 0XE8C1, 0XE981, 0X2940, 0XEB01, 0X2BC0, 0X2A80, 0XEA41,
	0XEE01, 0X2EC0, 0X2F80, 0XEF41, 0X2D00, 0XEDC1, 0XEC81, 0X2C40,
	0XE401, 0X24C0, 0X2580, 0XE541, 0X2700, 0XE7C1, 0XE681, 0X2640,
	0X2200, 0XE2C1, 0XE381, 0X2340, 0XE101, 0X21C0, 0X2080, 0XE041,
	0XA001, 0X60C0, 0X6180, 0XA141, 0X6300, 0XA3C1, 0XA281, 0X6240,
	0X6600, 0XA6C1, 0XA781, 0X6740, 0XA501, 0X65C0, 0X6480, 0XA441,
	0X6C00, 0XACC1, 0XAD81, 0X6D40, 0XAF01, 0X6FC0, 0X6E80, 0XAE41,
	0XAA01, 0X6AC0, 0X6B80, 0XAB41, 0X6900, 0XA9C1, 0XA881, 0X6840,
	0X7800, 0XB8C1, 0XB981, 0X7940, 0XBB01, 0X7BC0, 0X7A80, 0XBA41,
	0XBE01, 0X7EC0, 0X7F80, 0XBF41, 0X7D00, 0XBDC1, 0XBC81, 0X7C40,
	0XB401, 0X74C0, 0X7580, 0XB541, 0X7700, 0XB7C1, 0XB681, 0X7640,
	0X7200, 0XB2C1, 0XB381, 0X7340, 0XB101, 0X71C0, 0X7080, 0XB041,
	0X5000, 0X90C1, 0X9181, 0X5140, 0X9301, 0X53C0, 0X5280, 0X9241,
	0X9601, 0X56C0, 0X5780, 0X9741, 0X5500, 0X95C1, 0X9481, 0X5440,
	0X9C01, 0X5CC0, 0X5D80, 0X9D41, 0X5F00, 0X9FC1, 0X9E81, 0X5E40,
	0X5A00, 0X9AC1, 0X9B81, 0X5B40, 0X9901, 0X59C0, 0X5880, 0X9841,
	0X8801, 0X48C0, 0X4980, 0X8941, 0X4B00, 0X8BC1, 0X8A81, 0X4A40,
	0X4E00, 0X8EC1, 0X8F81, 0X4F40, 0X8D01, 0X4DC0, 0X4C80, 0X8C41,
	0X4400, 0X84C1, 0X8581, 0X4540, 0X8701, 0X47C0, 0X4680, 0X8641,
	0X8201, 0X42C0, 0X4380, 0X8341, 0X4100, 0X81C1, 0X8081, 0X4040
	]



CRC16_INIT  = 0xffff

def pwrcmd_crc_init(leng):
	crc = CRC16Iteration(CRC16_INIT, (leng >> 8) & 0xff)

	ret = CRC16Iteration(crc, (leng >> 0) & 0xff)
	#print ("<pwrcmd_crc_init> leng =" , leng, "ret =", hex(ret))
	return ret



	
def CRC16Iteration(crc, data):
	bval = (data ^ crc) & 255
	#print ("bval, data, crc =", hex(bval), hex(data), hex(crc))
	ret = (crc >> 8) ^ wCRCTable[bval]
	#print ("[CRC16Iter: ", hex(crc), ", ", hex(data), " -> ", hex(ret))
	return ret



def CRC16(data, length, init):
	crc = init
	#print ("Checking CRC on", data, length)
	for i in range(0, length):
		#print (i, ": ", hex(data[i]))
		bval = (data[i] ^ crc) & 255
		crc = (crc >> 8) ^ wCRCTable[bval]

	#print ("\n -> CRC is %x\n", hex(crc))
	return crc



# Transmit a power command (1-byte value) 

def pwrcmd_command(cmd):
	crc = CRC16Iteration(pwrcmd_crc_init(1), cmd);
	buf = [
		PWRCMD_SOF_VALUE,   # Start-of-Frame 
		0, 1,               # Length
		cmd,                # Command
		(crc >> 8) & 0xff,
		(crc >> 0) & 0xff 
	]
	#print ("<pwrcmd_command>", cmd, ": crc is ", end='');
	#print ( hex(crc), "\n");
	ser.write(buf)
	return 0


def CheckCRC(clist):
	crc = CRC16(clist[1:], len(clist) - 3, CRC16_INIT);
	#print ("crc is", hex(crc))
	if  crc == (clist[-2] << 8) + clist[-1]:
		return True
	print ("CRC from power controller failed!")
 

