
# Camera class
#from mem import fpga_mmio

from memobj import MemObject
from sensorobj import SensorObject
from lux1310 import Lux1310Object


class CamObject:
	#print("CamObject created")
	# mem = MemObject()


	#print ("begin")
	mem = MemObject()
	#sensor = SensorObject(mem)
	sensor = Lux1310Object(mem)
	


	def setLiveTiming(self, geometry, hOutRes, vOutRes, maxFPS):

		pxClock = 100000000
		hSync = 50
		hPorch = 166
		vSync = 3
		vPorch = 38

		hPeriod = hOutRes + hSync + hPorch + hSync

		# Calculate minimum hPeriod to fit within the max vertical
		# resolution and make sure hPeriod is equal to or larger
	 
		minHPeriod = (pxClock / ((sensor.v_max_res + vPorch + vSync + vSync) * maxFps)) + 1; # the +1 is just to round up
		if hPeriod < minHPeriod: 
			hPeriod = minHPeriod

		# calculate vPeriod and make sure it's large enough for the frame
		vPeriod = pxClock / (hPeriod * maxFps)
		if vPeriod < (vOutRes + vSync + vPorch + vSync):
			vPeriod = vOutRes + vSync + vPorch + vSync
	



# minHPeriod;
# hPeriod;
# vPeriod;
# fps;


# def cam_init(cam):

# 	frame_words = 0
# 	maxfps = 3




#print ("cam begin")

#camobj = CamObject()

#camobj.mem.mm_print()
