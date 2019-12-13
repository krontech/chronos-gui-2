# -*- coding: future_fstrings -*-

def µsShortHuman(µs: float, maxWidth: int = 6) -> {'units': str, 'value': float, 'decimals': int}:
	"""Slightly inaccurate human-readable formatting data for microseconds.
	
		Args:
			µs: Some number of microseconds.
			maxWidth: The number of characters to use when formatting, including
				unit. The default, 6, usually has 3-4 significant places and a
				1-2 character unit. Higher values will yeild more significant
				places. For example; at 6 width, we get microseconds up to 4
				digits. After that, we get a decimal ms value. At width 8, we
				get microseconds up to 6 digits, after which we get a decimal ms
				value with more digits to the left.
		
		Return: {
			unit string, 
			value number, 
			decimals places,
		}
		
		The is split out like this because we use it to format spin boxes.
	"""
	
	#output examples - no good reason, just what looked about right
	# 16.6m
	# 999s
	# 200s
	# 34.54s 
	# 1.145s
	# 1.10s
	# 999ms
	# 99.2ms
	# 10.0ms
	# 9999µs
	# 99µs
	# 9.9µs
	
	scale = 10**maxWidth / 10**6 #This is the scalar for the decimal point. Default is 6.
	
	# 9.9µs
	if µs < 10:
		return {
			'unit': 'µs',
			'value': µs,
			'decimals': 1,
		}
		
	# 99µs
	# 9999µs
	if µs < 10000 * scale:
		return {
			'unit': 'µs',
			'value': µs,
			'decimals': 0,
		}
		
	# 10.0ms
	# 99.2ms
	if µs < 1e5 * scale:
		return {
			'unit': 'ms',
			'value': µs/1000,
			'decimals': 1,
		}
		
	# 9999ms
	if µs < 1e6 * scale:
		return {
			'unit': 'ms',
			'value': µs/1000,
			'decimals': 0,
		}
		
	# 10.57s
	if µs < 1e7 * scale:
		return {
			'unit': 's',
			'value': µs/1e6,
			'decimals': 2,
		}
		
	# 100s
	# 999s
	if µs < 1e8 * scale:
		return {
			'unit': 's',
			'value': µs/1e6,
			'decimals': 0,
		}
		
	# 16.6m
	return {
		'unit': 'm',
		'value': µs/1e6 / 60,
		'decimals': 1,
	}
	

def shortHumanToµs(number: str):
	"""Return µs value when given a str. eg, "9.5ms" → 9500."""
	raise NotImplementedError 
	

def µsToShortHuman(*args, **kwargs) -> str:
	"""Uses the information from µsShortHumanFormat to return a string."""
	
	formatData = µsShortHuman(*args, **kwargs)
	
	return f'{{:.{formatData.decimals}f}}{{:s}}'.format(
		formatData.value, 
		formatData.unit
	)


def µsToLongHuman(value: float) -> str:
	"""Add commas to a number to make it more readable."""
	raise NotImplementedError