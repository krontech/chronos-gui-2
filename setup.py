import os
import glob
from setuptools import setup
from distutils.cmd import Command
from distutils.command.build_py import build_py

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
		gendir = os.path.join(os.path.dirname(__file__), 'chronosGui2/generated')
		makeopts = ' --dry-run' if self.dry_run else ''
		os.system('make -C ' + gendir + makeopts)

# Generate some python code from Qt files.
class gui2_build_py(build_py):
	def run(self):
		# Call the super
		build_py.run(self)
		
		# Setup the options for the make.
		gendir = os.path.join(self.build_lib, 'chronosGui2/generated')
		genmake = os.path.join(os.path.dirname(__file__), 'chronosGui2/generated/Makefile')
		makeopts = '-C %s -f %s' % (gendir, os.path.abspath(genmake))
		if self.dry_run:
			makeopts += ' --dry-run'

		# Create the output directory.
		try:
			print('creating ' + gendir)
			if not self.dry_run:
				os.mkdir(gendir)
		except OSError as e:
			# It's okay for the directory to exist.
			pass
	
		# Run make to generate the PyQt UI files.
		os.system('make ' + makeopts)

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
