import os
import requests
from bs4 import BeautifulSoup as bs
import click
import re


def get_links(url, filter=None):
    """Return (filtered) links listed in an HTML table at a given URL.

    Args:
    	url: URL where listing is located
		link_filter (Optional[Callable[str, obj]]): Function to filter links.
			Should take the link as an argument and return ``None`` if link should
			not be added to list and an object (usually a dict or str) if it should.
			The object returned will be added to the list of links as is.

	Returns:
		List: A list of (possibly filtered) links. If no filter is provided, simply
			a list of the links themselves, as strings. If a filter is provided,
			a list of the output from the filter.

	>>> get_links('http://www2.census.gov/acs2005/summaryfile/', filter=lambda h: h if not h.find('/') >= 0 else None)
	[u'ACS_2005_SF_Tech_Doc.pdf', u'ACS_SF_Worked_Example.pdf', u'README.pdf']
	
	>>> len(get_links('http://www2.census.gov/acs2005/summaryfile/'))
	58

	"""
    r = requests.get(url)
    soup = bs(r.text)
    links = soup.select('td a') # get all links in a table cell

    if filter is not None:
    	# If filter is set, return the good (non "None") hrefs from the filter
    	return [goodlink for goodlink in (filter(link['href']) for link in links) if goodlink is not None]
    else:
    	# If no filter is set, just return the hrefs
    	return [link['href'] for link in links]

def link_filter(href):
	"""Clean and filter link href.

	Args:
		href (str): the href component of a link

	Returns:
		If href matches correct format, returns a dict with relevant
		components of href (and whole string).

		If href doesn't match, returns None.

	>>> self.link_filter('Alaska/')
	u'Alaska'

	>>> self.link_filter('/acs2005/')
	None
	"""
	clean_href = href[0:-1] # Remove trailing slash from links
	# This regex gets the year and duration from the name of the folder on the Census server
	acs_re = re.compile(r'acs(?P<y ear>[0-9]{4})(?:_(?P<dur>[135])yr)?$')
	m = acs_re.match(clean_href)
	if m is not None and int(m.group(1)) >= 2005: # only want folders for ACS from 2005 or later
		return {'dir': clean_href, 'match': m}
	else:
		return None

def get_state_dir(st, is2005=False):
    """Given a 2-char abbreviation, return the state directory.

    The Census standard is the full state name, camel case, spaces
    removed. This generally is true for "United States" too, but in 2005
    they put a "0" in front of the name, to make sure it's sorted to the top.

    Args:
    	st: 2-character abbreviation
    	is2005 (Optional): whether year is 2005

    Returns:
    	A string with the state's directory name
    """
    state = us.states.lookup(st)
    if state is None:
        if st.upper() == "US":
            if not is2005:
                return "UnitedStates"
            else:
                return "0UnitedStates"
    else:
        return state.name.replace(" ","")

def get_files(url, year, dur, states, mode="SF"):
	"""Get list of files to download from server.

	"""
	if mode=="PUMS":
		return [{'url': url,
					'file': 'unix_%s%s.zip' % (rectype, st),
					'state': st}
					for rectype in ('h', 'p')
				for st in states]
	else: # Summary File has weird standards
		# Start with empty list of files
		files = []
		if year==2009 and dur==1: # weird exception
            subdir = 'Entire_States/' 
        elif year !=2009 and dur == 1:
            # The subdirectory starts with the year covered.
            subdir = '%s_ACSSF_By_State_All_Tables/' % year
        else:
            # The subdirectory starts with the range of years covered
            start_yr = year - dur + 1
            subdir = '%s-%s_ACSSF_By_State_All_Tables/' % (start_yr, year)

        for st in states:
        	st_links = get_links(url + subdir, 
        						filter=lambda link:
        							link 
        								if re.search(r'%s.*\.zip' % get_state_dir(st), link)
        								else None




class CensusDownloader(object):
	"""Class to hold downloader context.

	"""
	
	def __init__(self, outdir,
				baseurl='http://www2.census.gov/', maxyear,
				years, durations, states):
		"""Init method"""
		self.baseurl = baseurl
		self.outdir = outdir
		self.link_filter = link_filter

	@property
	def outdir(self):
	    return self._outdir

	@outdir.setter
	def outdir(self, outdir):
		# Make sure directory exists. If not, create it.
		try:
			os.makedirs(outdir)
		except OSError:
			# If directory already exists, fine
			# otherwise, a real error, so raise it
			if not os.path.isdir(outdir):
				raise
		self._outdir = outdir

	@property
	def link_filter(self):
		return self._link_filter

	@property
	def remote_files(self):
		if self._remote_files is None:
			folders = get_links(self.baseurl, self.link_filter)


	    return self._remote_files


	@property
	def dest_files(self):
	    return self._dest_files




	def download(self):
		"""Download remote files to destination.

		"""
		for f in self.remote_files:
			download(url, path)

	
	

@click.group()
def dl_acs():
    """Example script."""
    click.echo()

@dl_acs.command()
def sf():
	"""Download Summary File datafiles"""
	click.echo("Downloading SF")

@dl_acs.command()
def pums():
	"""Download Public Use Microdata Sample datafiles"""
	click.echo("Downloading PUMS")