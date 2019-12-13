# -*- coding: future_fstrings -*-
import os
import logging; log = logging.getLogger('Chronos.gui')
from typing import Sequence

from PyQt5 import uic, QtWidgets, QtCore

import chronosGui2.api as api
import chronosGui2.settings as settings

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_Color
else:
	from chronosGui2.generated.chronos import Ui_Color

#Two abbreviations used on this page are WB for White Balance and CM for Colour Matrix.

presets = {
	"CIECAM16/D55": [
		+1.9147, -0.5768, -0.2342,
		-0.3056, +1.3895, -0.0969,
		+0.1272, -0.9531, +1.6492,
	],
	"CIECAM02/D55": [
		+1.2330, +0.6468, -0.7764,
		-0.3219, +1.6901, -0.3811,
		-0.0614, -0.6409, +1.5258,
	],
	"identity": [
		+1.0000, +0.0000, +0.0000,
		+0.0000, +1.0000, +0.0000,
		+0.0000, +0.0000, +1.0000,
	],
}


class Color(QtWidgets.QDialog, Ui_Color):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		#Color Temperature
		try:
			api.observe('wbTemperature', lambda temp:
				self.uiColorTemperature.setValue(temp) )
			self.uiColorTemperature.valueChanged.connect(lambda temp:
				api.set('wbTemperature', temp) )
		except AssertionError as e:
			log.error(f'could not connect widgets to wbTemperature')
		
		#White Balance Matrix
		try:
			api.observe('wbColor', lambda color: (
				self.uiWBRed.setValue(color[0]), 
				self.uiWBGreen.setValue(color[1]), 
				self.uiWBBlue.setValue(color[2]),
			))
			for wbInput in [self.uiWBRed, self.uiWBGreen, self.uiWBBlue]:
				wbInput.valueChanged.connect(lambda *_:
					api.set('wbColor', [
						self.uiWBRed.value(), 
						self.uiWBGreen.value(), 
						self.uiWBBlue.value(),
					]) )
		except AssertionError as e:
			log.error(f'could not connect widgets to wbColor')
		
		#Color Matrix Preset
		self.uiColorMatrixPreset.clear()
		self.uiColorMatrixPreset.insertItem(0, self.tr('CIECAM02/D55'), 'CIECAM02/D55')
		self.uiColorMatrixPreset.insertItem(1, self.tr('CIECAM16/D55'), 'CIECAM16/D55')
		self.uiColorMatrixPreset.insertItem(2, self.tr('Identity'), 'identity')
		self.uiColorMatrixPreset.insertItem(3, self.tr('Custom'), None)
		self.uiColorMatrixPreset.currentIndexChanged.connect(lambda index:
			self.setCM(
				presets[self.uiColorMatrixPreset.itemData(index)]
				if self.uiColorMatrixPreset.itemData(index) else
				settings.value('customColorMatrix', presets['identity'])
			)
		)
		
		#Color Matrix
		api.observe('colorMatrix', self.updateCMInputs)
		for cmInput in self.colorMatrixInputs():
			cmInput.valueChanged.connect(self.cmUpdated)
		
		#Navigation
		self.uiDone.clicked.connect(window.back)
	
	
	def setCM(self, colorMatrix: Sequence[int]) -> None: #9 long.
		api.set('colorMatrix', colorMatrix)
		self.updateCMInputs(colorMatrix)
	
	def updateCMInputs(self, colorMatrix: Sequence[int]) -> None: #9 long.
		for cmInput, multiplier in zip(self.colorMatrixInputs(), colorMatrix):
			cmInput.blockSignals(True)
			cmInput.setValue(multiplier)
			cmInput.blockSignals(False)
		self.updateCMPreset()
	
	
	def updateCMPreset(self) -> None:
		"""Set color matrix preset, based on what is displayed."""
		
		for index in range(self.uiColorMatrixPreset.count()):
			presetName = self.uiColorMatrixPreset.itemData(index)
			
			#Custom preset. Always true. Should be last element in list.
			if not presetName:
				settings.setValue('customColorMatrix',
					[cmInput.value() for cmInput in self.colorMatrixInputs()])
				break
			
			
			#Match one of the existing presets.
			preset = presets[presetName]
			if False not in [
				abs(presetValue - cmInput.value()) < 0.001
				for presetValue, cmInput in zip(preset, self.colorMatrixInputs())
			]:
				break
		
		self.uiColorMatrixPreset.setCurrentIndex(index)
	
	
	def cmUpdated(self, *_):
		api.set('colorMatrix', [cmInput.value() for cmInput in self.colorMatrixInputs()])
		self.colorMatrixInputs()
	
	
	def colorMatrixInputs(self) -> Sequence[int]: #9 long
		return [
			self.uiCMRedRed,
			self.uiCMRedGreen,
			self.uiCMRedBlue,
			self.uiCMGreenRed,
			self.uiCMGreenGreen,
			self.uiCMGreenBlue,
			self.uiCMBlueRed,
			self.uiCMBlueGreen,
			self.uiCMBlueBlue,
		]
