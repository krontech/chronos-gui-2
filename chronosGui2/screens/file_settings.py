# -*- coding: future_fstrings -*-
import os
import logging; log = logging.getLogger('Chronos.gui')

from PyQt5 import uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

import chronosGui2.api as api
import chronosGui2.settings as settings
from chronosGui2 import delay

# Import the generated UI form.
from chronosGui2.generated.chronos import Ui_FileSettings

class FileSettings(QtWidgets.QDialog, Ui_FileSettings):
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setGeometry(0,0, 800,480)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		# Hide some stuff we haven't programmed yet. (Filesize, file name preview.)
		for id_ in {
			'headerlabel_2', 'uiDiskSpaceVisualization',
			'frame', 'frame_2', 'frame_3',
			'uiDiskSpaceFree', 'uiDiskSpaceRequired', 'uiDiskSpaceUsed',
			'label_4', 'widget_2', 'label_5'
		}:
			getattr(self, id_).deleteLater()
			
			
			
		
		# Button binding.
		#The preferred external partition is the one set in settings' preferredFileSavingUUID, OR the most recent partition.
		settings.observe('preferredFileSavingUUID', '', self.setPreferredSavingDevice)
		api.externalPartitions.observe(lambda *_: self.setPreferredSavingDevice(
			settings.value('preferredFileSavingUUID', '') ))
		self.uiSavedVideoLocation.currentIndexChanged.connect(lambda *_: 
			self.uiSavedVideoLocation.hasFocus() and settings.setValue(
				'preferredFileSavingUUID',
				(self.uiSavedVideoLocation.currentData() or {}).get('uuid') ) )
		
		
		self.uiSavedVideoName.setText(
			settings.value('savedVideoName', self.uiSavedVideoName.text()) )
		self.uiSavedVideoName.textChanged.connect(lambda value:
			settings.setValue('savedVideoName', value) )
		
		self.uiSavedVideoFileExtention.setCurrentText(
			settings.value('savedVideoFileExtention', self.uiSavedVideoFileExtention.currentText()) )
		self.uiSavedVideoFileExtention.currentTextChanged.connect(lambda value:
			settings.setValue('savedVideoFileExtention', value) )
		
		
		self.uiSavedFileFramerate.setValue(
			settings.value('savedFileFramerate', self.uiSavedFileFramerate.value()) )
		self.uiSavedFileFramerate.valueChanged.connect(lambda value:
			settings.setValue('savedFileFramerate', value) )
		
		self.uiSavedFileBPP.setValue(
			settings.value('savedFileBPP', self.uiSavedFileBPP.value()) )
		self.uiSavedFileBPP.valueChanged.connect(lambda value:
			settings.setValue('savedFileBPP', value) )
		
		self.uiSavedFileMaxBitrate.setValue(
			settings.value('savedFileMaxBitrate', self.uiSavedFileMaxBitrate.value()) )
		self.uiSavedFileMaxBitrate.valueChanged.connect(lambda value:
			settings.setValue('savedFileMaxBitrate', value) )
		
		
		self.uiAutoSaveVideo.setCheckState( #[autosave]
			bool(settings.value('autoSaveVideo', self.uiAutoSaveVideo.checkState())) * 2 )
		self.uiAutoSaveVideo.stateChanged.connect(lambda value:
			settings.setValue('autoSaveVideo', bool(value)) )
		
		self.uiResumeRecordingAfterSave.setCheckState( #[autosave]
			bool(settings.value('resumeRecordingAfterSave', self.uiResumeRecordingAfterSave.checkState())) * 2 )
		self.uiResumeRecordingAfterSave.stateChanged.connect(lambda value:
			settings.setValue('resumeRecordingAfterSave', bool(value)) )
		
		
		self.uiFormatStorage.clicked.connect(lambda: window.show('storage'))
		self.uiDone.clicked.connect(window.back)
	
	
	
	def onShow(self):
		#Try, _again_, to set the drop-down to the correct value. Since this widget is
		#repopulated when the partitions change and on show, this is really hard. >_<
		api.externalPartitions.observe(lambda *_: self.setPreferredSavingDevice(
			settings.value('preferredFileSavingUUID', '') ))
		delay(self, 16, lambda:
			api.externalPartitions.observe(lambda *_: self.setPreferredSavingDevice(
				settings.value('preferredFileSavingUUID', '') )) )
	
	def setPreferredSavingDevice(self, device):
		try:
			self.uiSavedVideoLocation.setCurrentIndex(
				[partition['uuid'] for partition in api.externalPartitions.list()].index(device) )
		except ValueError: #Not found. Do nothing.
			pass
