# -*- coding: future_fstrings -*-

from copy import deepcopy

from PyQt5 import uic, QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QGraphicsOpacityEffect #Also available: QGraphicsBlurEffect, QGraphicsColorizeEffect, QGraphicsDropShadowEffect

from debugger import *; dbg
import api_mock as api
from api_mock import silenceCallbacks


settings = QtCore.QSettings('Krontech', 'back-of-camera interface')

allInputIds = (
	'uiTrigger1Action', 'uiTrigger1ThresholdVoltage', 'uiTrigger11mAPullup', 'uiTrigger120mAPullup', 'uiTrigger1Invert', 'uiTrigger1Debounce',
	'uiTrigger2Action', 'uiTrigger2ThresholdVoltage', 'uiTrigger2Invert', 'uiTrigger2Debounce', 'uiTrigger220mAPullup',
	'uiTrigger3Action', 'uiTrigger3ThresholdVoltage', 'uiTrigger3Invert', 'uiTrigger3Debounce',
	'uiMotionTriggerAction', 'uiMotionTriggerDebounce', 'uiMotionTriggerInvert',
)

visualizationPadding = (15, 20, 0, 20) #top, right, bottom, left; like CSS

highStrength = 1.0
lowStrength = 0.5

class Triggers(QtWidgets.QDialog):
	"""Trigger screen. Configure one IO trigger at a time.
	
		This screen is slightly unusual in that triggers are only
		applied when you hit "apply" or "done", instead of the usual
		apply-on-change. This is because these settings change
		electrical properties, and some configurations - such as
		changing a 1mA pullup to a 20mA pullup - could do physical
		damage. Having to hit another button provides some safety.
		
		Here are some notable variables involved:
			- triggerCapabilities: The properties of the each
				available trigger. Things like what type it is, what
				pullups are available, etc. These only change between
				models of camera, never on an individual camera.
			- triggerConfiguration: How the triggers are set up on
				this camera. When you hit Save or Done, this is what
				is saved.
			- triggerState: Which triggers are currently active. This
				can change extremely frequently, but is only polled
				every so often to avoid network congestion.
		"""
	
	#Save current screen by ID, not by index or display text because those are UI changes.
	#These map IDs to indexes, and must be updated when the .ui file combo box is updated!
	availableTriggerIds = ('trig1', 'trig2', 'trig3', 'motion')
	availableTrigger1Actions = ('none', 'record end', 'exposure gating', 'genlock in', 'genlock out')
	availableTrigger2Actions = ('none', 'record end', 'exposure gating', 'genlock in', 'genlock out')
	availableTrigger3Actions = ('none', 'record end')
	availableAnalog1Actions = ('none') #Analog triggers will be able to take action in the next version of triggers.
	availableAnalog2Actions = ('none') 
	availableMotionTriggerActions = ('none', 'record end')
	
	#Signals don't get to be debounced, that only applies to level-based triggers.
	signalBasedTriggers = ('exposure gating', 'genlock in', 'genlock out')
	
	#Output triggers are visualized differently than input triggers. They don't listen, they tell; so they output to their trigger instead of taking it as input.
	outputTriggers = ('genlock out')
	
	
	def __init__(self, window):
		super().__init__()
		uic.loadUi('src/screens/triggers.ui', self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		for id in allInputIds:
			obj = getattr(self, id)
			changedSignal = getattr(obj, 'currentIndexChanged', getattr(obj, 'valueChanged', getattr(obj, 'stateChanged', None))) #Couldn't just choose one, could we, QT. 😑
			changedSignal and changedSignal.connect(self.queueVisualizationRepaint)
			changedSignal and changedSignal.connect(self.markStateDirty)
		
		self.markStateClean() #Initialize. Comes in dirty from Qt Creator.
		self.uiSave.clicked.connect(self.markStateClean)
		self.uiCancel.clicked.connect(self.markStateClean)
		
		self.trigger3VoltageTextTemplate = self.uiTrigger3ThresholdVoltage.text()
		self.uiTrig1StatusTextTemplate = self.uiTrig1Status.text()
		self.uiTrig2StatusTextTemplate = self.uiTrig2Status.text()
		self.uiTrig3StatusTextTemplate = self.uiTrig3Status.text()
		self.uiMotionTriggerStatusTextTemplate = self.uiMotionTriggerStatus.text()
		
		# Set up panel switching.
		#DDR 2018-07-24 It's impossible to associate an identifier with anything in QT Designer. Painfully load the identifiers here. Also check everything because I will mess this up next time I add a trigger.
		if(self.uiActiveTrigger.count() != len(self.availableTriggerIds)):
			raise Exception("Trigger screen available trigger IDs does not match the number of textual entries in uiActiveTrigger.")
		if(self.uiTriggerScreens.count() != len(self.availableTriggerIds)):
			raise Exception("Trigger screen available trigger IDs does not match the number of uiTriggerScreens screens.")
		
		currentScreenId = settings.value('active trigger', self.availableTriggerIds[0])
		if(currentScreenId not in self.availableTriggerIds):
			print(f'{currentScreenId} is not a known trigger ID, defaulting to {self.availableTriggerIds[0]}')
			currentScreenId = self.availableTriggerIds[0]
		
		currentScreenIndex = self.availableTriggerIds.index(currentScreenId)
		self.uiActiveTrigger.setCurrentIndex(currentScreenIndex)
		self.changeShownTrigger(currentScreenIndex)
		
		self.uiActiveTrigger.currentIndexChanged.connect(self.changeShownTrigger)
		
		#We don't have motion triggering working yet, so we'll just remove it here…
		if currentScreenId != 'motion':
			self.uiActiveTrigger.removeItem(self.availableTriggerIds.index('motion'))
		
		#Set up state init & events.
		#self.uiSave.clicked.connect(lambda: self and dbg()) #Debug! \o/
		self.uiSave.clicked.connect(lambda: api.set({
			'triggerConfiguration': self.changedTriggerState()
		}))
		self.uiDone.clicked.connect(window.back)
		self.uiCancel.clicked.connect(lambda: 
			self.updateTriggerConfiguration(self.lastTriggerConfiguration))
		
		#OK, so, triggerCapabilities is a constant, that's good. Then
		#we have triggerConfiguration, which is one variable. We'll
		#watch that variable and just update everything when it changes
		#for now. A better way to do it would be to only update state
		#that changed since the last time it updated, so we don't wipe
		#state from unchanged sub-fields. (Note: The reason this is one
		#variable instead of many is that triggers are special, and
		#they need to be updated somewhat atomically. So one variable,
		#so you can't mess it up… I'm not sure this is the best design,
		#but it's what we decided on back when. We do variable
		#change aggregation for the sensor, we could do it here too.
		#But perhaps forcing it safe is a good decision, if less
		#convenient.) So, when *the* state updates, we'll just update
		#everything and it should work for now.
		
		#This shows the three times of data we have. One updates only once, one updates whenever the data is changed, and the final updates every frame.
		self.setCapabilities(api.get('triggerCapabilities'))
		
		self.lastTriggerConfiguration = None #Holds the state to update to when we hit save - not everything is directly representable in the interface, so we don't want to round-trip this out into the UI widgets and then back again.
		api.observe('triggerConfiguration', self.updateTriggerConfiguration)
		
		self.lastTriggerState = None
		
		#Set up the little fade effect on the trigger icons, indicating high and low.
		self.trigger1IconLevelEffect = QGraphicsOpacityEffect(self.uiTrigger1Icon)
		self.trigger2IconLevelEffect = QGraphicsOpacityEffect(self.uiTrigger2Icon)
		self.trigger3IconLevelEffect = QGraphicsOpacityEffect(self.uiTrigger3Icon)
		self.motionTriggerIconLevelEffect = QGraphicsOpacityEffect(self.uiMotionTriggerIcon)
		
		#self.uiTrigger1Icon.setGraphicsEffect(self.trigger1IconLevelEffect)
		#self.uiTrigger2Icon.setGraphicsEffect(self.trigger2IconLevelEffect)
		#self.uiTrigger3Icon.setGraphicsEffect(self.trigger3IconLevelEffect)
		#self.uiMotionTriggerIcon.setGraphicsEffect(self.motionTriggerIconLevelEffect)
		
		self.uiTrigger1Visualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiTrigger1Visualization, evt, 'trig1'))
		self.uiTrigger2Visualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiTrigger2Visualization, evt, 'trig2'))
		self.uiTrigger3Visualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiTrigger3Visualization, evt, 'trig3'))
		self.uiMotionTriggerVisualization.paintEvent = (lambda evt:
			self.paintVisualization(self.uiMotionTriggerVisualization, evt, 'motion'))
		
		self.triggerStateUpdateTimer = QtCore.QTimer()
		self.triggerStateUpdateTimer.timeout.connect(self.updateTriggerState)
		self.triggerStateUpdateTimer.setInterval(1000/3+0) #Update at 30fps since we're somewhat cpu-bound on this task.
		
		def setTrigger1ModifierVisibility(index: int) -> None:
			action = 'hide' if self.availableTrigger1Actions[index] in self.signalBasedTriggers else 'show'
			getattr(self.uiTrigger1Debounce, action)()
		self.uiTrigger1Action.currentIndexChanged.connect(setTrigger1ModifierVisibility)
		
		def setTrigger2ModifierVisibility(index: int) -> None:
			action = 'hide' if self.availableTrigger1Actions[index] in self.signalBasedTriggers else 'show'
			getattr(self.uiTrigger2Debounce, action)()
		self.uiTrigger2Action.currentIndexChanged.connect(setTrigger2ModifierVisibility)
	
	
	def onShow(self):
		#Don't poll the trigger states while hidden. But do show with accurate info when we start.
		self.updateTriggerState()
		self.triggerStateUpdateTimer.start()
		
	def onHide(self):
		self.triggerStateUpdateTimer.stop()
	
	
	def changeShownTrigger(self, index: int) -> None:
		self.uiTriggerScreens.setCurrentIndex(index)
		settings.setValue('active trigger', self.availableTriggerIds[index])
	
	
	def setCapabilities(self, config: dict) -> None:
		"""Configure the UI with the capabilities reported by the API.
		
			Note: Most of the capabilities are hard-coded into the .ui
			file right now. We only have one camera, so we only have
			one set of capabilities, so it doesn't make a lot of sense
			to pull this out right now.
		"""
		
		self.uiTrigger1ThresholdVoltage.setMinimum(config["trig1"]["thresholdMin"])
		self.uiTrigger1ThresholdVoltage.setMaximum(config["trig1"]["thresholdMax"])
		self.uiTrigger2ThresholdVoltage.setMinimum(config["trig2"]["thresholdMin"])
		self.uiTrigger2ThresholdVoltage.setMaximum(config["trig2"]["thresholdMax"])
	
	
	@pyqtSlot('QVariantMap', name="updateTriggerConfiguration")
	@silenceCallbacks(*allInputIds)
	def updateTriggerConfiguration(self, config: dict) -> None:
		"""Update the displayed trigger settings.
			
			Inverse of changedTriggerState.
			"""
		
		self.lastTriggerConfiguration = config #We're currently resetting all our inputs here, so reset trigger state too.
		
		self.uiTrigger1Action.setCurrentIndex(
			self.availableTrigger1Actions.index(config['trig1']['action']) )
		self.uiTrigger1ThresholdVoltage.setValue(config['trig1']['threshold'])
		self.uiTrigger11mAPullup.setChecked(config['trig1']['pullup1ma'])
		self.uiTrigger120mAPullup.setChecked(config['trig1']['pullup20ma'])
		self.uiTrigger1Invert.setChecked(config['trig1']['invert'])
		self.uiTrigger1Debounce.setChecked(config['trig1']['debounce'])
		self.uiTrigger1Debounce.setVisible(
			config['trig1']['action'] not in self.signalBasedTriggers )
		
		self.uiTrigger2Action.setCurrentIndex(
			self.availableTrigger2Actions.index(config['trig2']['action']) )
		self.uiTrigger2ThresholdVoltage.setValue(config['trig2']['threshold'])
		self.uiTrigger2Invert.setChecked(config['trig2']['invert'])
		self.uiTrigger2Debounce.setChecked(config['trig2']['debounce'])
		self.uiTrigger220mAPullup.setChecked(config['trig2']['pullup20ma'])
		self.uiTrigger2Debounce.setVisible(
			config['trig2']['action'] not in self.signalBasedTriggers )
		
		self.uiTrigger3Action.setCurrentIndex(
			self.availableTrigger3Actions.index(config['trig3']['action']) )
		self.uiTrigger3ThresholdVoltage.setText(
			self.trigger3VoltageTextTemplate.format(config['trig3']['threshold']) )
		self.uiTrigger3Invert.setChecked(config['trig3']['invert'])
		self.uiTrigger3Debounce.setChecked(config['trig3']['debounce'])
		
		#Most motion trigger settings are displayed in the motion trigger configuration screen.
		self.uiMotionTriggerAction.setCurrentIndex(
			self.availableMotionTriggerActions.index(config['motion']['action']) )
		self.uiMotionTriggerDebounce.setChecked(config['motion']['debounce'])
		self.uiMotionTriggerInvert.setChecked(config['motion']['invert'])
	
	def changedTriggerState(self) -> dict:
		"""Return trigger state, with the modifications made in the UI.
			
			Inverse of updateTriggerConfiguration.
			"""
		
		config = deepcopy(self.lastTriggerConfiguration) #Don't mutate the input, keep the model simple.
		
		config['trig1']['action'] = self.availableTrigger1Actions[self.uiTrigger1Action.currentIndex()]
		config['trig1']['threshold'] = self.uiTrigger1ThresholdVoltage.value()
		config['trig1']['pullup1ma'] = self.uiTrigger11mAPullup.checkState() == 2     #0 is unchecked [ ]
		config['trig1']['pullup20ma'] = self.uiTrigger120mAPullup.checkState() == 2   #1 is semi-checked [-]
		config['trig1']['invert'] = self.uiTrigger1Invert.checkState() == 2           #2 is checked [✓]
		config['trig1']['debounce'] = self.uiTrigger1Debounce.checkState() == 2
		
		config['trig2']['action'] = self.availableTrigger2Actions[self.uiTrigger2Action.currentIndex()]
		config['trig2']['threshold'] = self.uiTrigger2ThresholdVoltage.value()
		config['trig2']['invert'] = self.uiTrigger2Invert.checkState() == 2
		config['trig2']['debounce'] = self.uiTrigger2Debounce.checkState() == 2
		config['trig2']['pullup20ma'] = self.uiTrigger220mAPullup.checkState() == 2
		
		config['trig3']['action'] = self.availableTrigger3Actions[self.uiTrigger3Action.currentIndex()]
		config['trig3']['invert'] = self.uiTrigger3Invert.checkState() == 2
		config['trig3']['debounce'] = self.uiTrigger3Debounce.checkState() == 2
		
		#Most motion trigger settings are displayed in the motion trigger configuration screen.
		config['motion']['action'] = self.availableMotionTriggerActions[self.uiMotionTriggerAction.currentIndex()]
		config['motion']['debounce'] = self.uiMotionTriggerDebounce.checkState() == 2
		config['motion']['invert'] = self.uiMotionTriggerInvert.checkState() == 2
		
		return config
	
	
	def updateTriggerState(self):
		state = api.get('triggerState')
		if state == self.lastTriggerState:
			return #No action needed, nothing changed.
		self.lastTriggerState = state
		
		#Set trigger status indicators.
		self.uiTrig1Status.setText(
			self.uiTrig1StatusTextTemplate
				% ('● high' if state['trig1']['inputIsActive'] else '○ low') )
		self.uiTrig2Status.setText(
			self.uiTrig2StatusTextTemplate
				% ('● high' if state['trig2']['inputIsActive'] else '○ low') )
		self.uiTrig3Status.setText(
			self.uiTrig3StatusTextTemplate
				% ('● high' if state['trig3']['inputIsActive'] else '○ low') )
		self.uiMotionTriggerStatus.setText(
			self.uiMotionTriggerStatusTextTemplate
				% ('● high' if state['motion']['inputIsActive'] else '○ low') )
		
		#Set trigger icon effect.
		self.trigger1IconLevelEffect.setOpacity(highStrength if state['trig1']['inputIsActive'] else lowStrength)
		self.trigger2IconLevelEffect.setOpacity(highStrength if state['trig2']['inputIsActive'] else lowStrength)
		self.trigger3IconLevelEffect.setOpacity(highStrength if state['trig3']['inputIsActive'] else lowStrength)
		self.motionTriggerIconLevelEffect.setOpacity(highStrength if state['motion']['inputIsActive'] else lowStrength)
		
		#Mark visualization panes dirty, so they update appropriately.
		self.queueVisualizationRepaint()
	
	def markStateClean(self):
		self.uiUnsavedChangesWarning.hide()
		self.uiSave.hide()
		self.uiDone.show()
		self.uiCancel.hide()
		
	def markStateDirty(self):
		self.uiUnsavedChangesWarning.show()
		self.uiSave.show()
		self.uiDone.hide()
		self.uiCancel.show()
	
	def queueVisualizationRepaint(self):
		self.uiTrigger1Visualization.update()
		self.uiTrigger2Visualization.update()
		self.uiTrigger3Visualization.update()
		self.uiMotionTriggerVisualization.update()
	
	def paintVisualization(self, pane, event, triggerId):
		"""Paint the trigger level visualization pane.
			
			If the element + padding (which includes arrows) is wider
			than the remaining space, loop back to a new line. For each
			step of the process, highlight (or not) the trigger level.
			"""
		
		#print('paint', pane, event)
		#QPixmap("../../assets/qt_creator/check_box.svg")
		QPainter = QtGui.QPainter
		QPen = QtGui.QPen
		QPoint = QtCore.QPoint
		QColor = QtGui.QColor
		QFont = QtGui.QFont
		QPainterPath = QtGui.QPainterPath
		QImage = QtGui.QImage
		Qt = QtCore.Qt
		
		tinyFont = QFont("DejaVu Sans", 9, weight=QtGui.QFont.Thin)
		normalFont = QFont("DejaVu Sans", 11, weight=QtGui.QFont.Thin)
		
		visWidth = event.rect().width()
		
		#Output is assumed to always be high, so just always draw it black. There's some more work that needs to be done here.
		#Basically, we need a state that shows that something is a ~waveform~, not a level-based trigger. (eg, high/low)
		#We don't really have that at the moment, aside from "flickering madly".
		isOutputTrigger = False
		
		def strength(triggerIsActive: bool) -> float:
			return (
				highStrength 
				if triggerIsActive or isOutputTrigger else
				lowStrength
			)
		
		triggerState = self.lastTriggerState[triggerId]
		triggerIsActive = triggerState["inputIsActive"]
		
		painter = QPainter(pane)
		
		painter.setRenderHint(QPainter.Antialiasing, True)
		painter.setRenderHint(QPainter.TextAntialiasing, True)
		
		pen = QPen(QColor(0), 1, join=Qt.MiterJoin) #Miter join makes arrows look good.
		painter.setPen(pen)
		
		#x and y are the layout cursor. If we don't have enough room on a line (all elements are fixed-width) then we go to the next line.
		x = visualizationPadding[3]
		y = visualizationPadding[0]
		
		lineHeight = 42 #Calculated from the trigger icon + text.
		
		def drawArrow(toElementOfWidth: int) -> None:
			"""Draw an arrow to the next element, line-wrapping if needed."""
			nonlocal x, y 
			
			if x == visualizationPadding[3] and y == visualizationPadding[0]:
				return #We have not moved, must be at start. So don't draw arrow from nothing.
			
			arrowLength = 20 #px, always px
			arrowPadding = 10
			headSize = 5
			linePadding = 20
			
			painter.save()
			painter.translate(-0.5, -0.5) #Align 1px-width lines to the *center* of pixels when integer position specified, instead of the edges of pixels. If the line is exactly on a pixel edge, it will draw half the line on one pixel and the other half on the other, at half-strength due to the AA algorithm. 😑
			path = QPainterPath() #arrow line → or the ꙅ-type
			
			
			#Initial — of the arrow.
			x += arrowPadding
			path.moveTo(x, y + lineHeight//2)
			
			x += arrowLength
			path.lineTo(x, y + lineHeight//2)
			
			#Arrow wrap around to new-line.
			if x + arrowPadding + toElementOfWidth + arrowPadding + arrowLength > visWidth - visualizationPadding[1]: #Test if element + another arrow is over the right margin.
				path.lineTo(x, y + lineHeight + linePadding//2)
				x = visualizationPadding[3] + 5 #+ indent
				path.lineTo(x, y + lineHeight + linePadding//2)
				y += lineHeight + linePadding
				path.lineTo(x, y + lineHeight//2)
				x += arrowLength #Draw the arrow head again.
				path.lineTo(x, y + lineHeight//2)
			
			path.moveTo(x - headSize - 0.5, y + lineHeight//2 - headSize) #-0.5 to make AA line up just a little better for a more consistent line thickness
			path.lineTo(x, y + lineHeight//2)
			path.lineTo(x - headSize - 0.5, y + lineHeight//2 + headSize)
			
			x += arrowPadding
			
			painter.drawPath(path)
			painter.restore()
		
		
		def drawPullup() -> None:
			"""Draw the pullup that gets sent to IO."""
			nonlocal x
			
			painter.setOpacity(strength(1))
			
			pullupAmount = 0
			if triggerId == 'trig1':
				pullupAmount += self.uiTrigger11mAPullup.isChecked()*1
				pullupAmount += self.uiTrigger120mAPullup.isChecked()*20
			if triggerId == 'trig2':
				pullupAmount += self.uiTrigger220mAPullup.isChecked()*20
				
			if pullupAmount:
				#Draw the pullup amount.
				
				text = "5V at ≤%imA" % pullupAmount
				painter.setFont(normalFont)
				textHeight = painter.fontMetrics().height()
				textWidth = painter.fontMetrics().width(text)
				
				drawArrow(textWidth)
				
				painter.drawText(QPoint(
					x,
					y+lineHeight/2 + textHeight/4
				), text)
				
				x += textWidth
		
		
		def drawIoIcon() -> None:
			"""Compute height of icon + icon label, used for line height."""
			nonlocal x
			
			painter.setOpacity(strength(triggerIsActive))
			
			icon = QImage({
				'trig1': 'assets/images/bnc-connector.svg',
				'trig2': 'assets/images/green-connector.svg',
				'trig3': 'assets/images/green-connector-bottom.svg',
				'motion': 'assets/images/motion.svg',
			}[triggerId])
			if triggerId == 'motion':
				ioText = '{0:.1f}%'.format(triggerState["level"]*100)
			else:
				ioText = '{0:.2f}V'.format(triggerState["level"])
			iconWidth = icon.width()
			
			painter.setFont(tinyFont)
			textHeight = painter.fontMetrics().height()
			lineHeight = icon.height()-3+textHeight
			textWidth = painter.fontMetrics().width(ioText)
			totalWidth = max(iconWidth, textWidth)
			
			drawArrow(totalWidth)
			
			painter.drawImage(QPoint(
				x+(totalWidth-iconWidth)/2,
				y+3, #hack, visual weight was off though geometry was ok I think
			), icon)
			
			painter.setFont(tinyFont)
			painter.drawText(QPoint(
				x+(totalWidth-textWidth)/2, 
				y+3+lineHeight,
			), ioText)
			
			x += totalWidth
		
		
		def drawInversion() -> None:
			"""Draw "invert". Flip the active state."""
			nonlocal x, triggerIsActive
			
			if {
				'trig1': self.uiTrigger1Invert,
				'trig2': self.uiTrigger2Invert,
				'trig3': self.uiTrigger3Invert,
				'motion': self.uiMotionTriggerInvert,
			}[triggerId].isChecked():
				text = "Invert Signal"
				painter.setFont(normalFont)
				textHeight = painter.fontMetrics().height()
				textWidth = painter.fontMetrics().width(text)
				
				drawArrow(textWidth)
				
				painter.drawText(QPoint(
					x,
					y + lineHeight/2 + textHeight/4
				), text)
				
				triggerIsActive = not triggerIsActive
				painter.setOpacity(strength(triggerIsActive))
				
				x += textWidth
		
		
		def drawDebounce() -> None:
			"""Draw the debounce. Draw the debounce period under it."""
			nonlocal x
			
			if {
				'trig1': self.uiTrigger1Debounce,
				'trig2': self.uiTrigger2Debounce,
				'trig3': self.uiTrigger3Debounce,
				'motion': self.uiMotionTriggerDebounce,
			}[triggerId].isChecked():
				text = "Debounce"
				painter.setFont(normalFont)
				textWidth = painter.fontMetrics().width(text)
				
				drawArrow(textWidth)
				
				painter.drawText(QPoint(
					x,
					y + lineHeight/2
				), text)
				painter.setFont(tinyFont)
				painter.drawText(QPoint(
					x,
					y + lineHeight/2 + painter.fontMetrics().height()
				), "   (10ms)   ") #cheap-o center justification
				
				x += textWidth
		
		
		def drawTriggerAction() -> None:
			nonlocal x
			
			text = {
				'trig1': self.uiTrigger1Action,
				'trig2': self.uiTrigger2Action,
				'trig3': self.uiTrigger3Action,
				'motion': self.uiMotionTriggerAction,
			}[triggerId].currentText()
			
			if text == "None":
				text = "No Action"
			
			painter.setFont(normalFont)
			textHeight = painter.fontMetrics().height()
			textWidth = painter.fontMetrics().width(text)
			
			drawArrow(textWidth)
			
			painter.drawText(QPoint(
				x,
				y + lineHeight/2 + textHeight/4
			), text)
			
			x += textWidth
		
		
		action = {
			'trig1': self.availableTrigger1Actions[self.uiTrigger1Action.currentIndex()],
			'trig2': self.availableTrigger2Actions[self.uiTrigger2Action.currentIndex()],
			'trig3': self.availableTrigger3Actions[self.uiTrigger3Action.currentIndex()],
			'motion': self.availableMotionTriggerActions[self.uiMotionTriggerAction.currentIndex()],
		}[triggerId]
		
		if action in self.outputTriggers:
			isOutputTrigger = True
			
			drawTriggerAction()
			drawPullup()
			drawInversion()
			drawIoIcon()
		else:
			drawPullup()
			drawIoIcon()
			drawInversion()
			drawDebounce() if action not in self.signalBasedTriggers else None
			drawTriggerAction()