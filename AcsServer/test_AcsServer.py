from AcsServer import AcsServer
from nose.tools import assert_equals, with_setup
import sys
from nose.plugins.attrib import attr
# See http://nose.readthedocs.org/en/latest/plugins/attrib.html

@attr('slow') # Mark this test as a slow one, so we can exclude when running tests
def test_AcsServer_creation():
	for year in range(2005,2015):
		for durs in ([1], [1,3], [1,3,5]):
			for pums in (False, True):
				yield create_server, [year], list(durs), pums

def create_server(years, durs, pums):
	return AcsServer(years=years, durs=durs, pums=pums)

# def setup_module():
# 	print "Creating servers"
# 	sys.stdout.flush()
# 	global server_sf
# 	global server_pums
# 	server_sf = AcsServer(years=range(2005,2015), durs=[1,3,5], pums=False)
# 	server_pums = AcsServer(years=range(2005,2015), durs=[1,3,5], pums=False)


def test_SF_state_data_files_2005_1yr():
	print "Creating 2005 server"
	server = AcsServer(years=[2005], durs=[1], pums=False)
	assert_equals(
		server.state_data_files(2005, 1, ['ny','us', 'ma']),
		[{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2005/data/NewYork/all_ny.zip', 
			'state': 'ny'}, 
		{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2005/data/NewYork/nygeo.2005-1yr',
			'state': 'ny'}, 
		{'url': 
			'http://www2.census.gov/programs-surveys/acs/summary_file/2005/data/0UnitedStates/all_us.zip', 
			'state': 'us'},
		{'url': 
			'http://www2.census.gov/programs-surveys/acs/summary_file/2005/data/0UnitedStates/usgeo.2005-1yr',
			'state': 'us'},
		{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2005/data/Massachusetts/all_ma.zip', 
			'state': 'ma'}, 
		{'url': u'http://www2.census.gov/programs-surveys/acs/summary_file/2005/data/Massachusetts/mageo.2005-1yr', 
			'state': 'ma'}])


def test_SF_state_data_files_2009_13_5yr():
	print "Creating 2009/2013 server"
	server = AcsServer(years=[2009, 2013], durs=[1, 5], pums=False)
	assert_equals(server.state_data_files(2009, 5, ['ny']),
		[{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2009/data/5_year_by_state/NewYork_All_Geographies_Not_Tracts_Block_Groups.zip', 
			'state': 'ny'}, 
		{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2009/data/5_year_by_state/NewYork_Tracts_Block_Groups_Only.zip', 
			'state': 'ny'}])
	assert_equals(server.state_data_files(2013, 5, ['ny']),
		[{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2013/data/5_year_by_state/NewYork_All_Geographies_Not_Tracts_Block_Groups.zip', 
			'state': 'ny'}, 
		{'url': 
			u'http://www2.census.gov/programs-surveys/acs/summary_file/2013/data/5_year_by_state/NewYork_Tracts_Block_Groups_Only.zip', 
			'state': 'ny'}])

def test_PUMS_state_data_files():
	server = AcsServer(years=[2009, 2013], durs=[1, 5], pums=True)
	print server.state_data_files(2009, 1, ['ny', 'us'])


def test_pass():
	pass