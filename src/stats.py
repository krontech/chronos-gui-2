# -*- coding: future_fstrings -*-

from urllib.request import urlopen
import json

serial_number = -1
try:
	with open('/opt/camera/serial_number', 'r') as sn_file:
		serial_number = sn_file.read().strip()
except Exception:
	#OK, can't read that file. Fall back to MAC address.
	with open('/proc/net/arp') as arp_file:
		import re
		serial_number = re.search('(?:[\\d\\w:]{2,3}){6}', arp_file.read())[0]


app_version = 'unknown'
try:
	with open('git_description', 'r') as gd_file:
		app_version = gd_file.read().strip()
except Exception:
	pass

def report(tag: str, data: dict):
	"""Report program statistics to an internal server, stats.node.js."""
	
	assert tag
		
	data["tag"] = tag
	data["serial_number"] = serial_number #Always append this (hopefully) unique identifier.
	try:
		urlopen(
			'http://192.168.1.55:19861', 
			bytes(json.dumps(data), 'utf-8'),
			0.1,
		)
	except Exception:
		print('Could not contact local stats server.')
		pass
	
def report_mock(tag: str, data: dict):
	"""Report program statistics to nothing."""
	pass