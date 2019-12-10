from typing import Optional
from datetime import timedelta

import chronosGui2.api as api
import chronosGui2.settings as settings

def sizeForRaw12(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved as 12-bit RAW.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
	"""
	
	if hRes is None:
		hRes = api.apiValues.get('resolution')['hRes']
	if vRes is None:
		vRes = api.apiValues.get('resolution')['vRes']
	
	#Foobar, [11.10.19 16:22] The size of a DNG frame should be exactly (hres*vres*2) + 4096 bytes
	return (hRes*vRes*2) * frames + 200 #Add a little bit, 200 bytes, for file overhead.


def sizeForRaw16(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved as 16-bit RAW.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
	"""
	
	if hRes is None:
		hRes = api.apiValues.get('resolution')['hRes']
	if vRes is None:
		vRes = api.apiValues.get('resolution')['vRes']
	
	#Foobar, [11.10.19 16:22] The size of a DNG frame should be exactly (hres*vres*2) + 4096 bytes
	return (hRes*vRes*3) * frames + 200 #Add a little bit, 200 bytes, for file overhead.


def sizeForDng(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved as DNG.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
	"""
	
	if hRes is None:
		hRes = api.apiValues.get('resolution')['hRes']
	if vRes is None:
		vRes = api.apiValues.get('resolution')['vRes']
	
	#Foobar, [11.10.19 16:22] The size of a DNG frame should be exactly (hres*vres*2) + 4096 bytes
	return (hRes*vRes*2 + 4096) * frames + 200 #Add a little bit, 200 bytes, for file overhead.


def sizeForRgbTiff(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved as a color TIFF.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
	"""
	
	if hRes is None:
		hRes = api.apiValues.get('resolution')['hRes']
	if vRes is None:
		vRes = api.apiValues.get('resolution')['vRes']
	
	#Foobar, [11.10.19 16:24]: The size of an RGB TIFF file would be (hres*vres*3) + 4096
	return ((hRes*vRes*3) + 4096) * frames + 200 #Add a little bit, 200 bytes, for file overhead.


def sizeForMonoTiff(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved as black-and-white TIFF.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
	"""
	
	if hRes is None:
		hRes = api.apiValues.get('resolution')['hRes']
	if vRes is None:
		vRes = api.apiValues.get('resolution')['vRes']
	
	#Foobar, [11.10.19 16:24]: The size of a mono TIFF would be (hres*vres) + 4096
	return ((hRes*vRes*1) + 4096) * frames + 200 #Add a little bit, 200 bytes, for file overhead.


def sizeForTiffraw(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved as TIFFRAW.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
		
		Note:
			Unlike TIFF, there is no difference between color and mono
				footage in this format.
	"""
	
	#Foobar, [11.10.19 16:24]: The size of a TIFFRAW file wou be the same as a DNG.
	return sizeForDng(**locals())


def sizeForMp4(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None, *, frameRate: Optional[float] = None, bpp: Optional[float] = None, maxBitrate: Optional[float] = None) -> int:
	"""Estimate the size of a video saved as MP4.
		
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional, keyword-only): Number of frames-per-
				second, used for calculating bitrate internally. Computed
				value is capped by maxBitrate. Defaults to settings'
				savedFileBPP, which itself defaults to 0.7.
			bpp (float, optional, keyword-only): Bits-per-pixel of the video
				being recorded. Computed value is capped by maxBitrate.
				Defaults to settings' savedFileMaxBitrate, which itself
				defaults to 40.
			maxBitrate (float, optional, keyword-only): Cap megabits per
				second for the saved video. Mbps depends on resolution,
				frameRate, and bpp.

		Yields:
			int: The estimated size, in bytes, that the saved video might be.
		
		Note:
			This is less precise than other video formats' estimations due to
				the compression used by the format. Videos with more motion
				can take more room than videos with less, which we can't
				compensate for without analysis we can't afford.
	"""
	
	if hRes is None:
		hRes = api.apiValues.get('resolution')['hRes']
	if vRes is None:
		vRes = api.apiValues.get('resolution')['vRes']
	if frameRate is None:
		frameRate =  api.apiValues.get('frameRate')
	if bpp is None:
		bpp = settings.value('savedFileBPP', 0.7)
	if maxBitrate is None:
		maxBitrate = settings.value('savedFileMaxBitrate', 40)
	
	maxBitrate *= 1e6 #convert from mbps to bps
	bitrate = min(maxBitrate, hRes*vRes*frameRate*bpp)
	return frames/frameRate * bitrate + 200 #Add a little bit, 200 bytes, for file overhead.


def size(frames: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> int:
	"""Estimate the size of a video saved with the current camera settings.
		
		Args:
			frames (int): Number of frames in the video.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.

		Yields:
			int: The estimated size, in bytes, that the saved video will be.
	"""
	
	return (
		{
			'.raw': sizeForRaw12,
			'.dng': sizeForDng,
			'.tiff': 
				sizeForMonoTiff
				if api.apiValues.get('sensorColorPattern') == 'mono' else
				sizeForRgbTiff,
			'.tiff.raw': sizeForTiffraw,
			'.mp4': sizeForMp4,
		}
		[settings.value('savedVideoFileExtention', '.mp4')]
		(**locals())
	)




def durationForRaw12(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of a 12-bit RAW video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
	"""
	
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForRaw12(2000, hRes, vRes)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def durationForRaw16(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of a 16-bit RAW video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
	"""
	
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForRaw16(2000, hRes, vRes)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def durationForDng(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of a DNG video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
	"""
	
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForDng(2000, hRes, vRes)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def durationForRgbTiff(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of a color TIFF video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
	"""
	
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForRgbTiff(2000, hRes, vRes)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def durationForMonoTiff(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of a black-and-white TIFF video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
	"""
	
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForMonoTiff(2000, hRes, vRes)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def durationForTiffraw(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of a TIFFRAW video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
		
		Note:
			Unlike TIFF, there is no difference between color and mono
				footage in this format.
	"""
	
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForTiffraw(2000, hRes, vRes)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def durationForMp4(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None, frameRate: Optional[float] = None, *, bpp: Optional[float] = None, maxBitrate: Optional[float] = None) -> timedelta:
	"""Estimate the duration of an MP4 video of a known filesize.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The roughly estimated run time of the video.
		
		Note:
			This is less precise than other video formats' estimations due to
				the compression used by the format. Videos with more motion
				can take more room than videos with less, which we can't
				compensate for without analysis we can't afford.
	"""
		
	if frameRate is None:
		frameRate =  settings.value('savedFileFramerate', 30)
	
	sizeOfOneFrame = sizeForMp4(2000, hRes, vRes, frameRate=frameRate, bpp=bpp, maxBitrate=maxBitrate)/2000 #Lower error due to nonscaling overhead, ie, one-off headers are a significant chunk of a one-frame video, but irrelevant for a 100,000 frame video.
	totalFrames = int(filesize / sizeOfOneFrame)
	return timedelta(seconds=totalFrames / frameRate)


def duration(filesize: int, hRes: Optional[int] = None, vRes: Optional[int] = None) -> timedelta:
	"""Estimate the duration of a video saved using the current camera settings.
		
		Args:
			size (int): Number of bytes in the video file.
			hRes (int, optional): Horizontal size of the video. Defaults to
				the current size of video being recorded.
			vRes (int, optional): Vertical size of the video. Defaults to
				the current size of video being recorded.
			frameRate (float, optional): The number of frames per second the
				video being estimated plays back at. Defaults to settings'
				savedFileFramerate, which defaults to 30.

		Yields:
			timedelta: The estimated run time of the video.
	"""
	
	return (
		{
			'.raw': durationForRaw12,
			'.dng': durationForDng,
			'.tiff': 
				durationForMonoTiff
				if api.apiValues.get('sensorColorPattern') == 'mono' else
				durationForRgbTiff,
			'.tiff.raw': durationForTiffraw,
			'.mp4': durationForMp4,
		}
		[settings.value('savedVideoFileExtention', '.mp4')]
		(**locals())
	)