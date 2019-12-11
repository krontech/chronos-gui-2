from setuptools import setup

setup(
	name='chronosGui2',
	version='0.0.1',
	description='Chronos 1.4 back-of-camera Python QT 5 GUI',
	url='https://github.com/krontech/chronos-gui-2',
	author='David Roberts',
	author_email='ddr@krontech.ca',
	classifiers=[
		"License :: OSI Approved",
		"License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
		"Programming Language :: Python"
	],
	package_data={
		'': ['*.ui'],
		'chronosGui2': ['read_jog_wheel_encoder.c'],
	},
	entry_points={
		'console_scripts': [
			'chronosGui2=chronosGui2.__main__:main'
		]
	},
	install_requires=['pyqt5>=5.7'],
	packages=['chronosGui2', 'chronosGui2/widgets', 'chronosGui2/screens', 'chronosGui2/input_panels'],
	python_requires='>=3',
	license='GPLv3+'
)
