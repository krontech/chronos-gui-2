
from dataclasses import dataclass



@dataclass
class ImageGeometryData:
	hres: int = 1280
	vres: int = 1024
	hoffset: int = 0
	voffset: int = 0

# Image timing constraings are a function of the selected frame geometry, so this
# structure is to be returned by the ops->get_constraings function for a given
# X/Y resolution.


@dataclass
class ImageConstraintsData:
	t_min_period: int = 0
	t_max_period: int = 0

	# Exposure timing must satisfy the constraints:
	# tMinExposure <= tExposure <= (tFramePeriod * tMaxShutter) / 360 - tExposureDelay

	t_min_exposure: int = 0
	t_exposure_delay: int = 0
	t_max_shutter: int = 0

	# All timing values will be implicitly quantized by this frequency. */
	f_quantization: int = 0




'''
@dataclass
class image_sensor_ops {
	int (*set_exposure)(struct image_sensor *sensor, const struct image_geometry *g, unsigned long long nsec);
	int (*set_period)(struct image_sensor *sensor, const struct image_geometry *g, unsigned long long nsec);
	int (*set_resolution)(struct image_sensor *sensor, const struct image_geometry *g);
	int (*get_constraints)(struct image_sensor *sensor, const struct image_geometry *g, struct image_constraints *c);
	/* ADC Gain Configuration and Calibration */
	int (*set_gain)(struct image_sensor *sensor, int gain, FILE *cal);
	int (*cal_gain)(struct image_sensor *sensor, const struct image_geometry *g, const void *frame, FILE *cal);
	char *(*cal_suffix)(struct image_sensor *sensor, char *filename, size_t maxlen);
};
'''

def luxnum(self):
	return 5

class SensorObject():
	def __init__(self, mem):
		self.mem = mem

	# print ("class SensorObject")
	# print (mem)
	
	ImageGeometry = ImageGeometryData()
	ImageGeometry.hres = 500000001
	numfunc = luxnum

