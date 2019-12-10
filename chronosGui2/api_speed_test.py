#!/usr/bin/python3
# -*- coding: future_fstrings -*-
"""Speed test PyQt5's D-Bus implementation."""

from PyQt5 import QtWidgets
from debugger import *; dbg
import chronosGui2.api as api
import time

TEST_ITERATIONS = 100



app = QtWidgets.QApplication(sys.argv)

t1 = time.perf_counter()
print('test 1: simple calls to control api')
for x in range(TEST_ITERATIONS):
	api.control.callSync('get', ['batteryVoltage'])
	print('.', end='', flush=True)
print(f"""
Time: {time.perf_counter()-t1}s total, {(time.perf_counter()-t1)/TEST_ITERATIONS*1000}ms per call.
""")

t2 = time.perf_counter()
print('test 2: async calls to control api')
counter = 0
def configureValue(*_):
	global counter
	global t3
	counter += 1
	print('.', end='', flush=True)
	if not counter < TEST_ITERATIONS:
		print(f"""
Time: {time.perf_counter()-t2}s total, {(time.perf_counter()-t2)/TEST_ITERATIONS*1000}ms per call.
""")

		t3 = time.perf_counter()
		print('test 3: chained get calls')
		getBatteryVoltage(-1)

for x in range(TEST_ITERATIONS):
	api.control.call('get', ['batteryVoltage']).then(configureValue)

t3 = 0
x = 0
def getBatteryVoltage(*_):
	global x
	x = x + 1
	if x <= 100:
		print('.', end='', flush=True)
		api.get('batteryVoltage').then(getBatteryVoltage)
	else:
		print(f"""
Time: {time.perf_counter()-t3}s total, {(time.perf_counter()-t3)/TEST_ITERATIONS*1000}ms per call.
""")
		app.quit()


sys.exit(app.exec_())


"""
Results:

PyQt5.DBus; Unladen, no intercall time:
test 1: Time: 0.6735163000048487s total, 6.7353785000159405ms per call.
test 2: Time: 1.0611664000025485s total, 10.611879499992938ms per call.
test 3: Time: 1.0689314999981434s total, 10.68952249996073ms per call.

PyQt5.DBus; Unladen, 1ms intercall time:
test 1: Time: 0.6696369499986758s total, 6.696585999961826ms per call.
test 2: Time: 1.2051974499991047s total, 12.052213999995729ms per call.
test 3: Time: 1.1969613500041305s total, 11.969804000036675ms per call.


PyQt5.DBus; Laden, 1ms intercall time:
test 1: Time: 1.315425900000264s total, 13.154962500047986ms per call.
test 2: Time: 2.5850381999989622s total, 25.85057850003068ms per call.
test 3: Time: 2.7320590499948594s total, 27.320799000008265ms per call.

Twisted; Unladen:
test 1: Time: 0.4529215499997008s total, 4.5315949999985605ms per call.

Twisted; Laden:
test 1: Time: 1.6233974999995553s total, 16.234189500000866ms per call.

Notes:
1 frame is 16ms.
Test is getting battery voltage, since I think that's a quintisentially cheap operation.
Burdening tool was yes.
"""