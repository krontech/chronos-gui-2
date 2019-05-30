# -*- coding: future_fstrings -*-

from urllib.request import urlopen
import json
import logging; log = logging.getLogger('Chronos.perf')

serialNumber = -1
try:
	with open('/opt/camera/serial_number', 'r') as sn_file:
		serialNumber = sn_file.read().strip()
except Exception:
	#OK, can't read that file. Fall back to MAC address.
	with open('/proc/net/arp') as arp_file:
		import re
		serialNumber = re.search('(?:[\\d\\w:]{2,3}){6}', arp_file.read())[0]


appVersion = 'unknown'
try:
	with open('git_description', 'r') as gd_file:
		appVersion = gd_file.read().strip()
except Exception:
	pass


report_url = 'http://192.168.1.55:19861'
def report(tag: str, data: dict):
	"""Report program statistics to an internal server, stats.node.js."""
	assert tag
	assert "tag" not in data
	assert "serial_number" not in data
		
	data["tag"] = tag
	data["serial_number"] = serialNumber #Always append this (hopefully) unique identifier.
	try:
		urlopen(report_url, bytes(json.dumps(data), 'utf-8'), 0.1)
	except Exception:
		log.warn(f'Could not contact the stats server at {report_url}.')
		pass
	
def report_mock(tag: str, data: dict):
	"""Report program statistics to nothing."""
	pass