# -*- coding: future_fstrings -*-

from collections import deque
from math import copysign

from PyQt5 import uic, QtWidgets, QtCore, QtGui

from debugger import *; dbg

import api2

from functools import partial


chartDuration = 90 #minutes
chartPadding = { #in px
	"top": 20,
	"bottom": 40,
	"left": 40,
	"right": 100,
}
maxVoltage = 16 #The camera will probably self-destruct after this, so the chart being out of range is the least of our worries.


def pct2dec(val: str) -> float:
	"""Return the decimal representation of a percent; ie, "45%" → 0.45."""
	return int(val[:-1])/100
	
def dec2pct(val: float) -> str:
	"""Return the percent representation of a float; ie, 0.45 → "45%"."""
	return f'{round(val*100)}%'


def constrain(low: float, n: float, high: float) -> float:
	"""Like clamp(…), but for UI work so averages low and high is low is higher than high."""
	if(low >= high):
		return (low+high)/2
	return max(min(high, n), low)



class Power(QtWidgets.QDialog):
	def __init__(self, window):
		super().__init__()
		uic.loadUi("src/screens/power.ui", self)
		
		# Panel init.
		self.move(0, 0)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		
		self.labelUpdateTimer = QtCore.QTimer()
		self.labelUpdateTimer.timeout.connect(self.updateLabels)
		self.labelUpdateTimer.setInterval(2000) #ms
		
		chartPoints = self.uiChart.geometry().width() - chartPadding["left"] - chartPadding["right"]
		self.chartChargeHistory = deque(maxlen=chartPoints)
		self.chartVoltageHistory = deque(maxlen=chartPoints)
		
		self.updateChartData()
		self.chartUpdateTimer = QtCore.QTimer()
		self.chartUpdateTimer.timeout.connect(self.updateChartData)
		self.chartUpdateTimer.start(#ms per pixel, chart moves over 1px per point
			(chartDuration*60*1000) / (chartPoints) )
		#print(self.chartUpdateTimer.interval())
		
		self.uiChart.paintEvent = self.paintChart
		
		#Avoid the chart redrawing just a little early, and not catching a changed power-down level. 
		self.uiSafelyPowerDown.stateChanged.connect(self.uiChart.update)
		
		#Store the original levels for updatePowerDownThreshold to use if it has to regenerate the list.
		self.originalBatteryThresholdLevels = [
			pct2dec(self.uiPowerDownThreshold.itemText(i))
			for i in range(self.uiPowerDownThreshold.count())
		]
		
		self.uiVoltageLabel.formatString = self.uiVoltageLabel.text()
		self.uiChargeLabel.formatString = self.uiChargeLabel.text()
		
		api2.observe("saveAndPowerDownLowBatteryLevelNormalized", self.updatePowerDownThreshold)
		self.uiPowerDownThreshold.currentTextChanged.connect(lambda val:
			api2.set("saveAndPowerDownLowBatteryLevelNormalized", pct2dec(val)) )
		self.uiPowerDownThreshold.currentTextChanged.connect(self.uiChart.update)
		
		self.uiDone.clicked.connect(window.back)
	
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		self.updateLabels()
		self.labelUpdateTimer.start()
		
	def onHide(self):
		self.labelUpdateTimer.stop()
	
	@QtCore.pyqtSlot(float, name="updatePowerDownThreshold")
	@api2.silenceCallbacks('uiPowerDownThreshold')
	def updatePowerDownThreshold(self, threshold: float):
		targetText = dec2pct(threshold)
		textIndex = self.uiPowerDownThreshold.findText(targetText)
		
		if textIndex+1:
			self.uiPowerDownThreshold.setCurrentIndex(textIndex)
		else:
			#Interleave the current value into the combo box items. (Note: `setCurrentText` has no effect if the text isn't in the combo box.)
			#This allows us to reflect any value from the API, while still allowing change and change back. (At least for this session.)
			self.uiPowerDownThreshold.clear()
			self.uiPowerDownThreshold.addItems([
				dec2pct(threshold)
				for threshold in
				sorted(self.originalBatteryThresholdLevels + [threshold], reverse=True)
			])
			self.uiPowerDownThreshold.setCurrentText(targetText)
		
		self.uiChart.update()
	
	def updateLabels(self):
		self.uiChargeLabel.setText(
			self.uiChargeLabel.formatString.format(
				api2.getSync('batteryChargeNormalized')*100 ) )
		self.uiVoltageLabel.setText(
			self.uiVoltageLabel.formatString.format(
				api2.getSync('batteryVoltage') ) )
		
	def updateChartData(self):
		"""Always update the chart data, even when hidden, so we can look at it later."""
		cv = api2.getSync(['batteryChargeNormalized', 'batteryVoltage'])
		charge, voltage = cv['batteryChargeNormalized'], cv['batteryVoltage']
		
		if charge < 0 or voltage < 0:
			return #Charge/voltage haven't initialized yet, don't record anything.
		
		self.chartChargeHistory.appendleft(charge)
		self.chartVoltageHistory.appendleft(voltage)
		
		self.uiChart.update() #Invokes the paintChart method below if needed, where Qt decides "if needed".
		
	def paintChart(self, evt):
		QPainter = QtGui.QPainter
		QPen = QtGui.QPen
		QRectF = QtCore.QRectF
		QColor = QtGui.QColor
		QFont = QtGui.QFont
		QPainterPath = QtGui.QPainterPath
		
		chartTotalWidth = evt.rect().width()
		chartTotalHeight = evt.rect().height()
		chartLineWidth = chartTotalWidth - chartPadding["right"] - chartPadding["left"]
		chartLineHeight = chartTotalHeight - chartPadding["top"] - chartPadding["bottom"]
		
		def projectToPlotSpace(x,y):
			return [
				chartTotalWidth - chartPadding["right"] - x,
				chartPadding["top"] + chartLineHeight - y*chartLineHeight,
			]
		
		
		#evt has .rect() -> QRect and .region() -> QClipRegion functions.
		p = QPainter(self.uiChart)
		pen = QPen()
		normalFont = QFont("DejaVu Sans", 11, weight=QtGui.QFont.Thin)
		tinyFont = QFont("DejaVu Sans", 9, weight=QtGui.QFont.Thin)
		p.setRenderHint(QPainter.Antialiasing, True)
		p.setRenderHint(QPainter.TextAntialiasing, True)
		p.setFont(normalFont)
		
		#Draw chart outline
		p.setPen(pen)
		p.drawRect(QRectF(
			chartPadding["left"]+0.5, #So, drawing on the pixel x,y with a line width 1 means that x,y and x-1, y-1 each get colored in 0.5 of a line-width. Add 0.5 to the offset to make it crisp, so one pixel gets the whole line.
			chartPadding["top"]+0.5,
			chartLineWidth,
			chartLineHeight,
		))
		
		#Draw power-down line
		if self.uiSafelyPowerDown.isChecked():
			pen.setStyle(QtCore.Qt.DashLine)
			p.setPen(pen)
			p.setFont(tinyFont)
			powerDownThreshold = pct2dec(self.uiPowerDownThreshold.currentText())
			partial( #Work around lack of PEP-0448, introduced in python 3.5. #backport-from-5.11
				p.drawLine,
				*projectToPlotSpace(0, powerDownThreshold)
			)(*projectToPlotSpace(chartLineWidth-(20 if powerDownThreshold < 0.15 or powerDownThreshold > 0.77 else 0), powerDownThreshold)), #Don't draw the line over the voltage labels.)
			p.drawText(
				projectToPlotSpace(chartLineWidth, powerDownThreshold)[0] + 20,
				projectToPlotSpace(chartLineWidth, powerDownThreshold)[1] + (-3 if powerDownThreshold < 0.90 else 12),
				"Save & Power Down" )
			p.setFont(normalFont)
			pen.setStyle(QtCore.Qt.SolidLine)
			p.setPen(pen)
		
		#Draw time labels
		p.drawText(
			chartPadding["left"] + 2,
			chartTotalHeight - chartPadding["bottom"] + 15,
			"{:1.0f} minutes ago".format(chartDuration) )
		
		p.drawText(
			chartTotalWidth - chartPadding["right"] - 35,
			chartTotalHeight - chartPadding["bottom"] + 15,
			"Now" )
		
		
		#Charge and voltage take a moment to initialize.
		if not self.chartChargeHistory or not self.chartVoltageHistory:
			return
		
		chargeLabelLocation = projectToPlotSpace(-5, 
			constrain(0.04, self.chartChargeHistory[0], 0.96) ) #Don't let labels overflow the chart vertical area during normal use. (May still overflow under exceptional circumstances when voltage is extremely high or low.)
		voltageLabelLocation = projectToPlotSpace(-6, 
			constrain(0.04, self.chartVoltageHistory[0]/maxVoltage, 0.96) )
		
		#Plot and label battery charge and voltage.
		minSpaceBetweenLabels = 14 #px
		labelDelta = chargeLabelLocation[1] - voltageLabelLocation[1]
		if abs(labelDelta) < minSpaceBetweenLabels:
			print('a', chargeLabelLocation)
			labelAverageY = (chargeLabelLocation[1] + voltageLabelLocation[1])/2
			chargeLabelLocation[1] = labelAverageY + copysign(minSpaceBetweenLabels/2, labelDelta)
			voltageLabelLocation[1] = labelAverageY - copysign(minSpaceBetweenLabels/2, labelDelta)
			print('b', chargeLabelLocation)
		
		
		#Charge
		path = QPainterPath()
		path.moveTo(projectToPlotSpace(-4, 0)[0], chargeLabelLocation[1])
		for x,y in enumerate(self.chartChargeHistory):
			path.lineTo(*projectToPlotSpace(x,y))
		p.setPen(QColor(0x0d6987))
		p.drawPath(path)
		p.drawText(chargeLabelLocation[0], chargeLabelLocation[1]+6, "Charge")
		
		p.rotate(-90)
		p.drawText(
			-chartTotalHeight + chartPadding["bottom"] + 3,
			chartPadding["left"] - 4,
			"0%" )
		p.drawText(
			-chartPadding["top"] - 47,
			chartPadding["left"] - 4,
			"100%" )
		p.rotate(90)
		
		
		#Voltage
		path = QPainterPath()
		path.moveTo(projectToPlotSpace(-4, 0)[0], voltageLabelLocation[1])
		for x,y in enumerate(self.chartVoltageHistory):
			path.lineTo(*projectToPlotSpace(x,y/maxVoltage))
		p.setPen(QColor(0xd8750d))
		p.drawPath(path)
		p.drawText(voltageLabelLocation[0], voltageLabelLocation[1]+6, "Voltage" )
		
		p.rotate(-90)
		p.drawText(
			-chartTotalHeight + chartPadding["bottom"] + 3,
			chartPadding["left"] + 15,
			"0V" )
		p.drawText(
			-chartPadding["top"] - 35,
			chartPadding["left"] + 15,
			f"{maxVoltage}V" )
		p.rotate(90)