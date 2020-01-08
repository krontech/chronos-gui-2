# -*- coding: future_fstrings -*-
from collections import deque
from math import copysign
from functools import partial

from PyQt5 import QtWidgets, QtCore, QtGui

import chronosGui2.api as api
import chronosGui2.settings as settings
from chronosGui2.debugger import *; dbg

# Import the generated UI form.
if api.apiValues.get('cameraModel')[0:2] == 'TX':
	from chronosGui2.generated.txpro import Ui_Power
else:
	from chronosGui2.generated.chronos import Ui_Power

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



class Power(QtWidgets.QDialog, Ui_Power):
	powerDownThreshold = 0.05 #Used to be in API as saveAndPowerDownLowBatteryLevelNormalized, but this got taken out December 2019.
	
	def __init__(self, window):
		super().__init__()
		self.setupUi(self)
		
		# Panel init.
		self.setFixedSize(window.app.primaryScreen().virtualSize())
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
		
		settings.observe('dimScreenWhenNotInUse', False, self.uiDimScreen.setChecked)
		self.uiDimScreen.stateChanged.connect(lambda checked:
			settings.setValue('dimScreenWhenNotInUse', bool(checked)) )
		
		self.uiVoltageLabel.formatString = self.uiVoltageLabel.text()
		self.uiChargeLabel.formatString = self.uiChargeLabel.text()
		
		self.uiDone.clicked.connect(window.back)
	
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		self.updateLabels()
		self.labelUpdateTimer.start()
		
	def onHide(self):
		self.labelUpdateTimer.stop()
	
	def updateLabels(self):
		self.uiChargeLabel.setText(
			self.uiChargeLabel.formatString.format(
				api.getSync('batteryChargeNormalized')*100 ) )
		self.uiVoltageLabel.setText(
			self.uiVoltageLabel.formatString.format(
				api.getSync('batteryVoltage') ) )
		
	def updateChartData(self):
		"""Always update the chart data, even when hidden, so we can look at it later."""
		cv = api.getSync(['batteryChargeNormalized', 'batteryVoltage'])
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
				chartPadding["top"] + chartLineHeight - 1 - y * (chartLineHeight - 2),
			]
		
		
		#evt has .rect() -> QRect and .region() -> QClipRegion functions.
		p = QPainter(self.uiChart)
		pen = QPen()
		
		#Font more or less copied from main.py, where we set the app font.
		normalFont = QFont("Roboto", 11, weight=QtGui.QFont.Normal)
		normalFont.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.25)
		normalFont.setHintingPreference(QtGui.QFont.PreferNoHinting)
		
		tinyFont = QFont("Roboto", 9, weight=QtGui.QFont.Normal)
		tinyFont.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.25)
		tinyFont.setHintingPreference(QtGui.QFont.PreferNoHinting)
		
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
			partial( #Work around lack of PEP-0448, introduced in python 3.5. #backport-from-5.11
				p.drawLine,
				*projectToPlotSpace(0, self.powerDownThreshold)
			)(*projectToPlotSpace(chartLineWidth-(20 if self.powerDownThreshold < 0.15 or self.powerDownThreshold > 0.77 else 0), self.powerDownThreshold)), #Don't draw the line over the voltage labels.)
			p.drawText(
				projectToPlotSpace(chartLineWidth, self.powerDownThreshold)[0] + 20,
				projectToPlotSpace(chartLineWidth, self.powerDownThreshold)[1] + (-3 if self.powerDownThreshold < 0.90 else 12),
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
			labelAverageY = (chargeLabelLocation[1] + voltageLabelLocation[1])/2
			chargeLabelLocation[1] = labelAverageY + copysign(minSpaceBetweenLabels/2, labelDelta)
			voltageLabelLocation[1] = labelAverageY - copysign(minSpaceBetweenLabels/2, labelDelta)
		
		
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
