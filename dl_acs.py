import os
import requests
from bs4 import BeautifulSoup as bs
import click
import re
import us


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


def acs_year_dur_filter(href):
    """Clean and filter link href for ACS links.

    Args:
        href (str): the href component of a link

    Returns:
        If href matches correct format, returns a dict with relevant
        components of href (and whole string).

        If href doesn't match, returns None.

    >>> acs_year_dur_filter('Alaska/')
    None

    >>> acs_year_dur_filter('/acs2005/')
    {'dir': '/acs2005'}
    """
    #clean_href = href[0:-1] # Remove trailing slash from links
    # This regex gets the year and duration from the name of the folder on the Census server
    acs_re = re.compile(r'(?P<href>.*acs(?P<year>[0-9]{4})(?:_(?P<dur>[135])yr)?)(?:/?$)')
    m = acs_re.search(href)
    if m is not None and int(m.group('year')) >= 2005: # only want folders for ACS from 2005 or later
        return {'dir': m.group('href'), 'match': m}
    else:
        return None

def acs_folder(year, dur, rooturl='http://www2.census.gov/'):
    """Return the folder on the server for an ACS year and duration.

    """
    if year < 2007:
        return rooturl + 'acs{0}/'.format(year)
    else:
        return rooturl + 'acs{0}_{1}yr/'.format(year, dur)

def state_folder(year, dur, st, mode='SF', rooturl='http://www2.census.gov/'):
    """Return the folder on the server for an ACS year, duration, and state.

    A folder consists of the root URL, plus the ACS folder for a year/
    duration, plus some standard subdirectories, and then possibly a state
    subdirectory.


    """
    if year < 2007:
        folder = rooturl + 'acs{0}/'.format(year)
    else:
        folder = rooturl + 'acs{0}_{1}yr/'.format(year, dur)

    # For PUMS, all same subfolder
    if mode=="PUMS":
        return folder + 'pums/'

    # Otherwise:
    





def state_filestub(st, is2005=False):
    """Return the Census file stub (directory or filename) for a state.

    File stubs refer to a string that the Census uses both as a directory
    and as the filename (not including file extension).

    The Census standard is the full state name, camel case, spaces
    removed. This generally is true for "United States" too, but in 2005
    they put a "0" in front of the name, to make sure it's sorted to the top.

    Args:
        st: 2-character abbreviation
        is2005 (Optional): whether year is 2005

    Returns:
        A string with the state's directory name

    >>> state_filestub('ny')
    u'NewYork'

    >>> state_filestub('us')
    u'UnitedStates'

    >>> state_filestub('us', is2005=True)
    u'0UnitedStates'

    >>> state_filestub('qq')
    Exception
    ...
    """
    state = us.states.lookup(st)
    if state is None:
        if st.upper() == "US":
            if is2005:
                return u"0UnitedStates"
            else:
                return u"UnitedStates"
    else:
        return state.name.replace(" ","")


######################################
#### GET REMOTE FILE LISTS        ####
######################################
def get_acs_files(year, dur, states, mode="SF", rooturl='http://www2.census.gov/'):
    """Get list of files to download from server.

    The returned list is actually a list of dicts, with entries for the
    folder portion of the url, the actual file name, and then the state
    abbreviation.

    Args:
        year: the ACS year (the last year for multiyear estimates)
        dur: the ACS multiyear duration (1, 3, or 5)
        states (List[str]): a list of 2-letter state abbreviations (strings)
        mode (Optional): summary file ("SF") or PUMS ("PUMS"). Defaults to "SF"
        rooturl (Optional): the root URL. Defaults to 'http://www2.census.gov/'

    Returns:
        A list of dicts, where each dict represents a single file and has:
            'folder': the URL of the folder containing the file
            'file': the file name, including extension
            'state': the 2-letter abbreviation of the state

    Examples:
        In 2009 and after, the summary file is pretty standard

        >>> import pprint
        >>> get_acs_files(year=2009, dur=1, states=['NY', 'US'], mode='SF')
        ... #
        [{'folder': u'http://www2.census.gov/acs2009_1yr/summaryfile/Entire_States/',
            'file': u'NewYork.zip', 'state': 'NY'},
        {'folder': u'http://www2.census.gov/acs2009_1yr/summaryfile/Entire_States/',
            'file': u'UnitedStates.zip', 'state': 'US'}]


        In 2005, the US folder has a "0" at the beginning. Note the different names
        for the files, as well as state-specific folders on the server.

        >>> get_acs_files(year=2005, dur=1, states=['MA', 'US'], mode='SF')
        ... #
        [{'folder': u'http://www2.census.gov/acs2005/summaryfile/Massachusetts/',
            'file': u'all_ma.zip', 'state': 'MA'},
        {'folder': u'http://www2.census.gov/acs2005/summaryfile/0UnitedStates/',
            'file': u'all_us.zip', 'state': 'US'}]


        In 2006, the file names are different.
        >>> get_acs_files(year=2006, dur=1, states=['NJ', 'US'], mode='SF')
        [{'folder': u'http://www2.census.gov/acs2006/summaryfile/NewJersey/',
            'file': u'nj_all_2006.zip', 'state': 'NJ'},
        {'folder': u'http://www2.census.gov/acs2006/summaryfile/UnitedStates/',
            'file': u'us_all_2006.zip', 'state': 'US'}]

        Multiyear estimates example
        >>> get_acs_files(year=2013, dur=5, states=['NY', 'US'], mode='SF')
        None

        PUMS example.
        >>> get_acs_files(year=2009, dur=1, states=['NY', 'US'], mode='PUMS')
        None



    """
    if mode=="PUMS":
        # For PUMS, just return the list of person and household files
        return [{'url': url,
                    'file': 'unix_%s%s.zip' % (rectype, st),
                    'state': st}
                    for rectype in ('h', 'p')
                for st in states]

    else: # Summary File has weird standards
        # Get state directory from year, dur, state
        return get_files_new_SF(url, year, dur, states)


def get_files_new_SF(url, year, dur, states):
    """Get remote files using new SF standard.

    Starting in 2009, the Census is more consistent with the structure of
    the directories. There is one subdirectory within summaryfile/ that
    contains all the state files, each of which is just a single zipped file.
    Each state does NOT, thus, have a subdirectory itself.

    >>> get_files_new_SF('http://www2.census.gov/acs2009_1yr/summaryfile', 2009, 1, ['ny'])
    None

    """
    # Start with empty list of files
    files = []

    # Set subdirectory based on year and duration
    if year==2009 and dur==1: # weird exception
        subdir = 'Entire_States/' 
    elif year !=2009 and dur == 1: # single-year estimates except 2009
        # The subdirectory starts with the year covered.
        subdir = '%s_ACSSF_By_State_All_Tables/' % year
    else: # Multiyear estimates
        # The subdirectory starts with the range of years covered
        start_yr = year - dur + 1
        subdir = '%s-%s_ACSSF_By_State_All_Tables/' % (start_yr, year)

    # Return list of files in subdirectory for each state
    # Only want zip files
    for st in states:
        st_links = get_links(url + subdir)
        for link in st_links: 
            if re.search(r'%s.*\.zip' % get_state_dir(st), link):
                files.append({'url': st_dir, 'file': link, 'state': st})
    return files


def get_files_old_SF(url, year, dur, states):
    """Get remote file list using old SF standard.

    The Census, in its infinite wisdom, has very inconsistent naming conventions,
    but the greatest difference is that, before 2009, the summaryfile/ directory
    contains a subdirectory for each state, and within those subdirectories
    there is a listing of all the files as well as a zip file containing all
    those files. Thus the format is generally (with some exceptions):
    
    acsYEAR_DURyr/summaryfile/StateName/all_st.zip
    
    Where StateName is what is returned by get_state_dir(), basically
    the state name in camel case and without spaces, and st is the two-letter
    abbreviation (lowercase) for that state (or "us"). In 2005 and 2006, the outermost
    directory is just acsYEAR, without any duration (and those are both 1-year files).
    In 2006, moreover, the name of the actual zip files is different:
        st_all_2006.zip


    """
    # Start with empty list of files
    files = []

    for st in states:
        is2005 = (year==2005)
        st_dir = url + get_state_dir(st, is2005)
        st_links = get_links(st_dir)
        
        if is2005:
            st_file = "all_%s.zip" % st
            geo_file = "%sgeo.2005-1yr" % st
        elif "all_%s.zip" % st in st_links:
            st_file = "all_%s.zip" % st
            geo_file = "g%s%s%s.txt" % (year, dur, st)
        elif "%s_all_2006.zip" % st in st_links:
            st_file =  "%s_all_2006.zip" % st
            geo_file = "g%s%s%s.txt" % (year, dur, st)
        else:
            print "NO FILE: %s" % st, st_dir
            break
        
        files.append({'url': st_dir + '/', 'file': st_file, 'state': st})
        files.append({'url': st_dir + '/', 'file': geo_file, 'state': st})
    return files






class CensusDownloader(object):
    """Class to hold downloader context.

    """
    
    def __init__(self, outdir,
                baseurl='http://www2.census.gov/', mode="SF"):
        """Init method"""
        self.baseurl = baseurl
        self.outdir = outdir
        self.link_filter = link_filter
        self.mode = mode

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
@click.option('--baseurl', default='http://www2.census.gov/', help="Census root URL")
@click.option('--years', '-y', type=(click.INT, click.INT))
#@click.argument('outdir')
def sf(baseurl, years):
    """Download Summary File datafiles"""
    click.echo("Downloading SF %s" % years)

    mode = "SF"
    #get_files_new_SF(url, year, dur, states)

@dl_acs.command()
def pums():
    """Download Public Use Microdata Sample datafiles"""
    click.echo("Downloading PUMS")