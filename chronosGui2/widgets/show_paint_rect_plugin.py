from os import environ
from random import randrange

from PyQt5.QtGui import QPainter, QColor


class ShowPaintRectsPlugin():
	if (environ.get('CHRONOS_SHOW_PAINT_RECTS') or 'n')[0].lower() == 'y':
		def paintEvent(self, evt):
			"""Visualise update rects."""
			super().paintEvent(evt)
			
			p = QPainter(self)
			p.setClipRegion(evt.region())
			p.fillRect(
				0,0, 10000,10000,
				QColor.fromHsv(
					randrange(0,360),
					randrange(200,256),
					randrange(200,256),
					100
				)
			)