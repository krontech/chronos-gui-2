from dataclasses import dataclass
from struct import Struct

'''
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

# TODO: rebuild thes dataclasses as const? enum? hmmm...
#
# Do them as Struct.struct?

@dataclass
class FPGASeq:
	control: int = 0
	status: int = 0
	frame_size: int = 0
	region_start: int = 0
	region_stop: int = 0
	live_addr: int = 0
	trig_delay: int = 0
	md_fifo_read: int = 0


@dataclass
class FPGADisplay:
	control: int = 0
	frame_address: int = 0
	fpn_address: int = 0
	gain: int = 0
	h_period: int = 0
	v_period: int = 0
	h_sync_len: int = 0
	v_sync_len: int = 0
	h_back_porch: int = 0
	v_back_porch: int = 0
	h_res: int = 0
	v_res: int = 0
	h_out_res: int = 0
	__reserved0: int = 0
	v_out_res: int = 0
	peaking_thresh: int = 0
	pipeline: int = 0
	__reserved1: int = 0
	manual_sync: int = 0


# Video RAM readout
@dataclass
class FPGAVram:
	identifier: int = 0
	version: int = 0
	subver: int = 0
	control: int = 0
	status: int = 0
	__reserved0[3]: int = 0
	address: int = 0
	burst: int = 0
	__reserved1: int = 0 # Align to offset 0x200 

VRAM_IDENTIFIER			= 0x40

VRAM_CTL_TRIG_READ		= (1 << 0)
VRAM_CTL_TRIG_WRITE		= (1 << 1)

@dataclass
class FPGAOverlay:
	# Overlay control registers. 
	identifier: int = 0    # Always reads 0x0055
	version: int = 0
	subver: int = 0
	control: int = 0
	status: int = 0
	text0_xpos: int = 0
	text0_ypos: int = 0
	text0_xsize: int = 0
	text0_ysize: int = 0
	text1_xpos: int = 0
	text1_ypos: int = 0
	text1_xsize: int = 0
	text1_ysize: int = 0
	wmark_xpos: int = 0
	wmark_ypos: int = 0
	text0_xoffset: int = 0
	text1_xoffset: int = 0
	text0_yoffset: int = 0
	text1_yoffset: int = 0
	logo_xpos: int = 0
	logo_ypos: int = 0
	logo_xsize: int = 0
	logo_ysize: int = 0
	text0_abgr: int = 0
	text1_abgr: int = 0
	wmark_abgr: int = 0
	__reserved0: int = 0 # Align to offset 0x100 
'''