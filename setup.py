import os
import glob
from setuptools import setup
from distutils.cmd import Command
from distutils.command.build_py import build_py

# Generate python code from Qt source files.
def generate(build_lib, dry_run):
	gendir = os.path.join(build_lib, 'generated')
	try:
		print('creating ' + gendir)
		if not dry_run:
			os.mkdir(gendir)
	except OSError as e:
		# It's okay for the directory to exist.
		pass

	# Generate the assets.py file.
	assetFile = os.path.join(gendir, 'assets.py')
	print('generating ' + assetFile)
	if not dry_run:
		os.system('pyrcc5 assets.qrc -o ' + assetFile)
	
	# Generate the UI files.
	for name in glob.glob('chronosGui2/screens/*.ui'):
		base = os.path.split(name)[1]
		output = os.path.join(gendir, os.path.splitext(base)[0] + '.py')
		print('generating ' + output)
		if not dry_run:
			os.system('pyuic5 ' + name + ' -o ' + output)

# Generate ui files for developement.
class gui2_build_ui(Command):
	"""A custom command to generate UI files."""
	description = 'Generate PyQt UI files.'
	user_options = []

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass
	
	def run(self):
		generate(os.path.join(os.path.dirname(__file__), 'chronosGui2'), self.dry_run)

# Generate some python code from Qt files.
class gui2_build_py(build_py):
	def run(self):
		# Call the super
		build_py.run(self)

		# Honor the --dry-run flag
		generate(os.path.join(self.build_lib, 'chronosGui2'), self.dry_run)

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
	packages=['chronosGui2', 'chronosGui2/widgets', 'chronosGui2/screens', 'chronosGui2/input_panels'],
	python_requires='>=3',
	license='GPLv3+',
	# Command overrides
	cmdclass={
		'build_py': gui2_build_py,
		'build_ui': gui2_build_ui
	}
)
