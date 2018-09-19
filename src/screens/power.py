from collections import deque
from math import copysign

from PyQt5 import uic, QtWidgets, QtCore, QtGui

from debugger import *; dbg
import api_mock as api


chartDuration = 120 #minutes
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
		
		#Store the original levels for updatePowerDownThreshold to use if it has to regenerate the list.
		self.originalBatteryThresholdLevels = [
			pct2dec(self.uiPowerDownThreshold.itemText(i))
			for i in range(self.uiPowerDownThreshold.count())
		]
		
		self.uiVoltageLabel.formatString = self.uiVoltageLabel.text()
		self.uiChargeLabel.formatString = self.uiChargeLabel.text()
		
		api.observe("saveAndPowerDownLowBatteryLevel", self.updatePowerDownThreshold)
		self.uiPowerDownThreshold.currentTextChanged.connect(
			lambda val: api.set({"saveAndPowerDownLowBatteryLevel":
				pct2dec(val) }) )
		
		self.uiDone.clicked.connect(window.back)
	
	def onShow(self):
		#Don't update the labels while hidden. But do show with accurate info when we start.
		self.updateLabels()
		self.labelUpdateTimer.start()
		
	def onHide(self):
		self.labelUpdateTimer.stop()
	
	@QtCore.pyqtSlot(float, name="updatePowerDownThreshold")
	@api.silenceCallbacks('uiPowerDownThreshold')
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
				sorted(self.originalBatteryThresholdLevels + [threshold])
			])
			self.uiPowerDownThreshold.setCurrentText(targetText)
	
	def updateLabels(self):
		self.uiChargeLabel.setText(
			self.uiChargeLabel.formatString.format(
				api.get('batteryCharge') ) )
		self.uiVoltageLabel.setText(
			self.uiVoltageLabel.formatString.format(
				api.get('batteryVoltage') ) )
		
	def updateChartData(self):
		"""Always update the chart data, even when hidden, so we can look at it later."""
		self.chartChargeHistory.appendleft(api.get('batteryCharge'))
		self.chartVoltageHistory.appendleft(api.get('batteryVoltage'))
		self.uiChart.update() #Invokes the paintChart method below if needed, where Qt decides "if needed".
		
	def paintChart(self, evt):
		QPainter = QtGui.QPainter
		QRect = QtCore.QRect
		QColor = QtGui.QColor
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
		p.setRenderHint(QPainter.Antialiasing, True)
		p.setRenderHint(QPainter.TextAntialiasing, True)
		
		#Draw chart outline and labels
		p.setPen(QColor(0x000))
		p.drawRect(QRect(
			chartPadding["left"],
			chartPadding["top"],
			chartLineWidth,
			chartLineHeight,
		))
		
		p.drawText(
			chartPadding["left"],
			chartTotalHeight - chartPadding["bottom"] + 15,
			"{:1.0f} hours ago".format(chartDuration/60) )
		
		p.drawText(
			chartTotalWidth - chartPadding["right"] - 38,
			chartTotalHeight - chartPadding["bottom"] + 15,
			"Now" )
		
		p.rotate(-90)
		
		p.drawText(
			-chartTotalHeight + chartPadding["bottom"] + 2,
			chartPadding["left"] - 3,
			"0%" )
		
		p.drawText(
			-chartPadding["top"] - 49,
			chartPadding["left"] - 3,
			"100%" )
		
		p.rotate(90)
			
		chargeLabelLocation = projectToPlotSpace(-5, 
			constrain(0.04, self.chartChargeHistory[0], 0.96) ) #Don't let labels overflow the chart vertical area during normal use. (May still overflow under exceptional circumstances when voltage is extremely high or low.)
		voltageLabelLocation = projectToPlotSpace(-6, 
			constrain(0.04, self.chartVoltageHistory[0]/maxVoltage, 0.96) )
		
		
		minSpaceBetweenLabels = 14 #px
		labelDelta = chargeLabelLocation[1] - voltageLabelLocation[1]
		if abs(labelDelta) < minSpaceBetweenLabels:
			print('a', chargeLabelLocation)
			labelAverageY = (chargeLabelLocation[1] + voltageLabelLocation[1])/2
			chargeLabelLocation[1] = labelAverageY + copysign(minSpaceBetweenLabels/2, labelDelta)
			voltageLabelLocation[1] = labelAverageY - copysign(minSpaceBetweenLabels/2, labelDelta)
			print('b', chargeLabelLocation)
		
		#Plot battery charge
		#(An alternative possible in js' canvas - but not here - is to have a ring buffer where each point is relative to the previous, and then go along writing more points to make everything move over. That can't work here because the drawing commands are absolute, not relative. Although it might be possible to write into an array of them, it is probably more work than is worth it, assuming this performs better than "abysmally".)
		path = QPainterPath()
		path.moveTo(*projectToPlotSpace(0, self.chartChargeHistory[0]))
		for x,y in enumerate(self.chartChargeHistory):
			path.lineTo(*projectToPlotSpace(x,y))
		p.setPen(QColor(0x0d6987))
		p.drawPath(path)
		p.drawText(chargeLabelLocation[0], chargeLabelLocation[1]+5, "Charge")
		
		#Plot battery voltage
		#(An alternative possible in js' canvas - but not here - is to have a ring buffer where each point is relative to the previous, and then go along writing more points to make everything move over. That can't work here because the drawing commands are absolute, not relative. Although it might be possible to write into an array of them, it is probably more work than is worth it, assuming this performs better than "abysmally".)
		path = QPainterPath()
		path.moveTo(*projectToPlotSpace(0, self.chartVoltageHistory[0]/maxVoltage))
		for x,y in enumerate(self.chartVoltageHistory):
			path.lineTo(*projectToPlotSpace(x,y/maxVoltage))
		p.setPen(QColor(0xd8750d))
		p.drawPath(path)
		p.drawText(voltageLabelLocation[0], voltageLabelLocation[1]+5, "Voltage" )
		
		
		
		p.end()
		#QtWidgets.QWidget.paintEvent(self, evt)