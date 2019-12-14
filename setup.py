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
def git_version():
	try:
		vers = subprocess.check_output(['git', 'describe', '--tags', '--always'],
			stderr=subprocess.DEVNULL)
		return vers.decode('utf-8').strip()
	except:
		pass

	try:
		verdata = {}
		with open(os.path.join(gendir, 'version.py')) as fp:
			exec(fp.read(), verdata)
		return verdata['__version__']
	except:
		return 'unknown'

# PEP-440 imposes its own version requirements, which differ from what
# we get in a git-describe. So tokenize the git version and translate.
def py_version(gitvers):
	# Start with the leading part of the version.
	vchunks = gitvers.split('-')
	output = vchunks[0]

	for x in vchunks[1:]:
		# Translate pre-release names.
		if x == 'alpha':
			output += 'a'
		elif x == 'beta':
			output += 'b'
		elif x.startswith('rc'):
			output += x
		# If it's a pure integer, then it's probably a rev-count.
		elif x.isdigit():
			output += '.post' + x
			break
		# Otherwise, interpret this as a local version.
		else:
			output += '+' + x

	return output

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
		generate(self.dry_run)

# Generate some python code from Qt files.
class gui2_build_py(build_py):
	def run(self):
		# Build generated code.
		generate(self.dry_run)

		# Call the super
		build_py.run(self)
		
class gui2_sdist(sdist):
	#sdist = source distribution
	def run(self):
		# Build generated code.
		generate(self.dry_run)

		# Call the super.
		sdist.run(self)

setup(
	name='chronosGui2',
	version=py_version(git_version()),
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
