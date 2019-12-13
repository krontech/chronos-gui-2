import os
import glob
import subprocess
from setuptools import setup
from distutils.cmd import Command
from distutils.command.build_py import build_py
from distutils.command.sdist import sdist

# Build the generated content.
gendir = os.path.join(os.path.dirname(__file__), 'chronosGui2/generated')
def generate(dry_run=False):
	makeopts = ' --dry-run' if dry_run else ''
	os.system('make -C ' + gendir + makeopts)

# Return the package version - either by querying the git
# repository, or falling back to the generated version.py
# from the source distribution.
def get_version():
	try:
		vers = subprocess.check_output(['git', 'describe', '--tags', '--always'],
			stderr=subprocess.DEVNULL)
		return vers.decode('utf-8').strip()
	except:
		verdata = {'__version__': 'unknown'}
		with open(os.path.join(gendir, 'version.py')) as fp:
			exec(fp.read(), verdata)
		return verdata['__version__']

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
		genenerate(self.dry_run)

# Generate some python code from Qt files.
class gui2_build_py(build_py):
	def run(self):
		# Build generated code.
		generate(self.dry_run)

		# Call the super
		build_py.run(self)
		
class gui2_sdist(sdist):
	def run(self):
		# Build generated code.
		generate(self.dry_run)

		# Call the super.
		sdist.run(self)

setup(
	name='chronosGui2',
	version=get_version(),
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
		'chronosGui2': ['forms/*.ui', 'read_jog_wheel_encoder.c'],
		'chronosGui2/generated': ['*.qrc'],
	},
	entry_points={
		'console_scripts': [
			'chronosGui2=chronosGui2.__main__:main'
		]
	},
	packages=[
		'chronosGui2',
		'chronosGui2/widgets',
		'chronosGui2/screens',
		'chronosGui2/input_panels',
		'chronosGui2/generated',
		'chronosGui2/generated/chronos',
		'chronosGui2/generated/txpro',
	],
	data_files=[('/etc/', ['util/chronos-gui2.conf'])],
	license='GPLv3+',
	# Command overrides
	cmdclass={
		'build_py': gui2_build_py,
		'build_ui': gui2_build_ui,
		'sdist': gui2_sdist
	}
)
