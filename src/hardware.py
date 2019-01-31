# -*- coding: future_fstrings -*-

import os, signal
from pathlib import Path
from typing import Callable, Optional
from subprocess import call, check_output, Popen, PIPE
from fcntl import fcntl, F_GETFL, F_SETFL

from PyQt5.QtCore import QTimer

from debugger import *; dbg

class Hardware():
	"""Access camera hardware, such as the jog wheel and status LEDs.
		
		Warning: Do not initialize more than one Hardware class. You
		only have one set of inputs, and only one thing can read from
		them. If two things read, every other event will be dropped.
		
		Properties:
			LEDs (write-only): Assign True or False to light or darken.
				- backRecordingLightLit
				- frontRecordingLightLit
				- recordingLightsLit
			
			Jog Wheel (read-only): True if button is being held down.
				- jogWheelPressed
			
			Record Button (read-only): True if button is being held down.
				- recordButtonReleased
		
		Functions:
			subscribe(event:str, callback:func):
				Invoke callback when event happens.
	"""
	
	def __init__(self):
		"""Fire events at the app as physical inputs are pressed."""
		
		#Create GPIO files if not existing.
		gpioPath = Path('/sys/class/gpio')
		gpios = [20,26,27,66,41,25] #general purpose input/output
		for gpio in gpios:
			if not (gpioPath/'gpio{}'.format(gpio)).exists():
				(gpioPath/'export').write_text('{}\n'.format(gpio))
				(gpioPath/'gpio{}'.format(gpio)/'edge').write_text('both\n')
				41 == gpio and (gpioPath/'gpio41/direction').write_text('out\n') #Default is 'in'.
				25 == gpio and (gpioPath/'gpio25/direction').write_text('out\n')
		
		#GPIO 20 and 26 are quite high frequency, and need to be checkd more frequently than we can here. (ie, drawing blocks for multiple ms, but we need to check every ms at least.)
		#They're shelled out to a little C program which aggregates them.
		encoderReader = 'src/read_jog_wheel_encoder'
		if not Path(encoderReader).exists():
			print('Compiling jog wheel encoder reader application…') #Should be cached, so this should not show up every time!
			if call([f'gcc {encoderReader}.c -O3 -o {encoderReader}'], shell=True):
				raise Exception('Could not compile required jog wheel reader application.')
			print('Done.')
		
		#Clean up after previous runs, if any spare jog wheel readers are left over.
		for pid in str(check_output(['pgrep', 'read_jog_wheel'], stdout=PIPE), 'utf-8').split('\n'):
			pid and call(['kill', pid])
		
		encoderProcess = Popen([encoderReader], stdout=PIPE)
		signal.signal(signal.SIGINT, #Kill encoder process when we exit.
			lambda sig, frame: os.kill(encoderProcess.pid, signal.SIGTERM))
		self._jogWheelEncoders = encoderProcess.stdout
		flags = fcntl(self._jogWheelEncoders, F_GETFL)
		fcntl(self._jogWheelEncoders, F_SETFL, flags | os.O_NONBLOCK)
		
		#This was sort of ported from the C++ app, but with fewer threads because I couldn't figure out what it was doing. Take caution: This is probably "working incorrect" code.
		self._jogWheelSwitch     = os.fdopen(os.open(gpioPath/"gpio27/value", os.O_RDONLY, 0), 'rb', buffering=0)
		self._recordButtonSwitch = os.fdopen(os.open(gpioPath/"gpio66/value", os.O_RDONLY, 0), 'rb', buffering=0)
		self._topLED             = os.fdopen(os.open(gpioPath/"gpio41/value", os.O_WRONLY, 0), 'wb', buffering=0)
		self._backLED            = os.fdopen(os.open(gpioPath/"gpio25/value", os.O_WRONLY, 0), 'wb', buffering=0)
		
		#Remember state to detect edges.
		self._jogWheelEncoderALast = 0
		self._jogWheelEncoderBLast = 0
		self._jogWheelPressedLast = False
		self._recordButtonReleasedLast = True
		
		self.subscriptions = {
			"jogWheelHighResolutionRotation": [],
			"jogWheelLowResolutionRotation": [],
			"jogWheelDown": [],
			"jogWheelUp": [],
			"jogWheelHeld": [], #not implemented
			"recordButtonDown": [],
			"recordButtonUp": [],
		}
		
		#Pump events. Jog wheel is handled by another program, since it needs to be polled in a blocking manner.
		self.lowResolutionTimer = QTimer()
		self.lowResolutionTimer.timeout.connect(self.__updateButtonStates)
		self.lowResolutionTimer.start(16) #ms, 1/frame @ 60fps
	
	
	def subscribe(self, eventName:str, callback:Callable[[Optional[int]], None]) -> None:
		"""Invoke callback when event happens.
			
			Use: subscribe(event:str, callback:func)
			
			Example:
				hardware = Hardware() #Only instantiate this once!
				hardware.subscribe('recordButtonDown', 
					lambda: print('down') )
			
			Valid events are:
				- jogWheelHighResolutionRotation
					Fired when the jog wheel is rotated, 4x/detent.
					Callback is passed ±1 indicating (clock) direction.
				- jogWheelLowResolutionRotation
					Fired when the jog wheel is rotated, 1x/detent.
					Callback is passed ±1 indicating (clock) direction.
				- jogWheelDown
					Jog wheel is depressed.
				- jogWheelUp
					Jog wheel is released.
				- jogWheelHeld (unimplimented)
					Jog wheel is "long-pressed", ie, held for one
					second without rotation.
				- recordButtonDown
					The red record button is held down.
				- recordButtonUp
					The red record button is released.
		"""
		self.subscriptions[eventName] += [callback]

	
	
	def __updateButtonStates(self):
		"""Update button states, firing events if state has changed.
			
			Takes care of jog wheel switch, record button switch, and jog wheel encoder logic.
		"""
		
		self._jogWheelSwitch.seek(0)
		jogWheelPressed = True if self._jogWheelSwitch.read(1) == b'1' else False
		if(jogWheelPressed != self._jogWheelPressedLast):
			self._jogWheelPressedLast = jogWheelPressed
			if jogWheelPressed:
				for callback in self.subscriptions["jogWheelDown"]:
					callback()
			else:
				for callback in self.subscriptions["jogWheelUp"]:
					callback()
		
		
		self._recordButtonSwitch.seek(0)
		recordButtonReleased = True if self._recordButtonSwitch.read(1) == b'1' else False
		if(recordButtonReleased != self._recordButtonReleasedLast):
			self._recordButtonReleasedLast = recordButtonReleased
			if recordButtonReleased:
				for callback in self.subscriptions["recordButtonUp"]:
					callback()
			else:
				for callback in self.subscriptions["recordButtonDown"]:
					callback()
		
		
		#Jog wheel encoder in detent with EncA = 1, EncB = 1. Clockwise rotation results in first change being EncA <- 0;
		highResDelta = 0 #High resolution jog wheel rotation. We get four deltas per detent. More suited for use with fine-grained controls such as sliders.
		lowResDelta = 0 #Like highResDelta, but only one delta per detent (or "notch"). More suited to coarser controls such as drop-down menus (comboboxes).
		
		#Can't readlines() here, never returns since we could turn the jog wheel forever.
		while True:
			line = self._jogWheelEncoders.readline()
			if len(line) == 0:
				break
			if len(line) != 3:
				print('got partial jog wheel encoder line') #This shouldn't happen because we flush() in the writer. Since this system is single-threaded, and lines are short, we should never see unflushed lines.
				break
				
			jogWheelEncoderA = True if line[0] == ord(b'1') else False
			jogWheelEncoderB = True if line[1] == ord(b'1') else False
			if(jogWheelEncoderA and not self._jogWheelEncoderALast): #rising edge
				if(jogWheelEncoderB):
					highResDelta -= 1
				else:
					highResDelta += 1
			elif(not jogWheelEncoderA and self._jogWheelEncoderALast): #falling edge
				if(jogWheelEncoderB):
					highResDelta += 1
				else:
					highResDelta -= 1
			
			if(jogWheelEncoderB and not self._jogWheelEncoderBLast): #rising edge
				if(jogWheelEncoderA):
					highResDelta += 1
				else:
					highResDelta -= 1
					lowResDelta -= 1
			elif(not jogWheelEncoderB and self._jogWheelEncoderBLast): #falling edge
				if(jogWheelEncoderA):
					highResDelta -= 1
				else:
					highResDelta += 1
					lowResDelta += 1
			
			self._jogWheelEncoderALast = jogWheelEncoderA
			self._jogWheelEncoderBLast = jogWheelEncoderB
		
		
		if not highResDelta:
			#nothing happened
			return
		
		for callback in self.subscriptions["jogWheelHighResolutionRotation"]:
			callback(highResDelta)
			
		if lowResDelta:
			for callback in self.subscriptions["jogWheelLowResolutionRotation"]:
				callback(lowResDelta)
	
	
	@property
	def backRecordingLightIsLit(self):
		raise Exception("Can't read back LED.")
	
	@backRecordingLightIsLit.setter
	def backRecordingLightIsLit(self, lit: bool):
		self._backLED.write(b'1' if lit else b'0')
	
	@property
	def topRecordingLightIsLit(self):
		raise Exception("Can't read an LED.")
	
	@topRecordingLightIsLit.setter
	def topRecordingLightIsLit(self, lit: bool):
		self._topLED.write(b'1' if lit else b'0')
	
	@property
	def recordingLightsAreLit(self):
		raise Exception("Can't read an LED.")
	
	@recordingLightsAreLit.setter
	def recordingLightsAreLit(self, lit: bool):
		self._topLED.write(b'1' if lit else b'0')
		self._backLED.write(b'1' if lit else b'0')
	
	
	@property
	def jogWheelPressed(self) -> bool:
		"""True if the jog wheel is pressed."""
		return self._jogWheelPressedLast
		
	@property
	def recordButtonPressed(self) -> bool:
		"""True if the record button is pressed."""
		return not self._recordButtonReleasedLast