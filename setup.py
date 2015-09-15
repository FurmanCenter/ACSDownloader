from setuptools import setup

setup(
	name='dl_acs',
	version='0.1',
	py_modules=['dl_acs'],
	install_requires=[
		'Click',
		'requests',
		'beautifulsoup4'
	],
	entry_points='''
		[console_scripts]
		dl_acs=dl_acs:dl_acs
	''',
)

