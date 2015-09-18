import os
import requests
from bs4 import BeautifulSoup as bs
import click
import re
import us
import logging
import pprint
#from colorama import Fore, Back, Style
#from colorama import init as colorama_init
#from termcolor import colored

import concurrent.futures

# Make termcolor work on Windows
#colorama_init()
import chromalog
from chromalog.mark.helpers.simple import important, success
logger = logging.getLogger(__name__)
for handler in logging.root.handlers:
    handler.addFilter(logging.Filter(__name__))
#logging.critical("TEST CHROMALOG")
#logger.critical("Testing Chromalog")

def safe_make_dir(newdir):
    try:
        os.makedirs(newdir)
    except OSError:
        # If can't create directory because it already exists, then fine.
        # But if it doesn't already exist, there's some other
        # problem and we should raise the exception
        if not os.path.isdir(newdir):
            raise

def download(url, path, chunk_size=1024*1024):
    """Download a file from a url to a file path

    Keyword arguments:
    url -- the URL of the file to be downloaded
    path -- the file path to serve as destination for downloaded file
    chunk_size -- the size of the file chunks (defaults to 1024^2)

    Returns a dictionary with following keys:
    'success' -- Boolean for whether downloaded without error
    'status' -- the status code
    """
    r = requests.get(url, stream=True)
    if r.status_code != requests.codes.ok:
        logger.error("Got status %s from %s" % (r.status_code, url))
        return {'success': False, 'status': r.status_code, 'url': url, 'path': path}
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        with click.progressbar(r.iter_content(chunk_size=chunk_size), label="Downloading {0}".format(os.path.split(r.url)[1])) as bar:
            for chunk in bar:
                if chunk:
                    f.write(chunk)
                    f.flush()

        # for chunk in progress.bar(r.iter_content(chunk_size=chunk_size), expected_size=(total_length/chunk_size) + 1): 
        #     if chunk:
        #         f.write(chunk)
        #         f.flush()
    return {'success': True, 'status': r.status_code, 'url': url, 'path': path}

def get_links(url, link_filter=None):
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
    soup = bs(r.text, "html.parser")
    links = soup.select('td a')  # get all links in a table cell

    if link_filter is not None:
        # If filter is set, return the good (non "None") hrefs from the filter
        return [goodlink for goodlink in
                [link_filter(link['href']) for link in links]
                if goodlink is not None]
    else:
        # If no filter is set, just return the hrefs
        return [link['href'] for link in links]


def acs_year_dur_filter(href, years=None, durs=None):
    """Clean and filter link href for ACS links.

    Args:
        href (str): the href component of a link
        years (Optional[iterable]): a list of years to accept
        durs (Optional[iterable]): a list of durations to accept

    Returns:
        If href matches correct format, returns a dict with relevant
        components of href (and whole string).

        If href doesn't match, returns None.

    >>> print acs_year_dur_filter('Alaska/')
    None

    >>> acs_year_dur_filter('/acs2005/') == {
    ...     'dir': 'acs2005', 
    ...     'dur': None, 
    ...      'href': '/acs2005',
    ...      'year': '2005'}
    True

    >>> acs_year_dur_filter('http://www2.census.gov/acs2009_5yr/') == {
    ...    'dir': '/acs2009_5yr', 
    ...    'dur': '5', 
    ...    'href': 'http://www2.census.gov/acs2009_5yr', 
    ...    'year': '2009'}
    True

    >>> print acs_year_dur_filter('http://www2.census.gov/acs2009_5yr/', years=[2009], durs=[3])
    None

    """
    # clean_href = href[0:-1] # Remove trailing slash from links
    # This regex gets the year and duration from the name of the folder on the
    # Census server
    acs_re = re.compile(
        r'(?P<href>.*(?P<dir>acs(?P<year>[0-9]{4})(?:_(?P<dur>[135])yr)?))(?:/?$)')
    m = acs_re.search(href)
    # if m is not None:
    #     print m.groups()
    # else:
    #     print "NO MATCH"
    # only want folders for ACS from 2005 or later
    if m is not None and int(m.group('year')) >= 2005:
        if m.group('year') is not None:
            year = int(m.group('year'))

        if m.group('dur') is not None:
            dur = int(m.group('dur'))
        else:
            dur = 1

         # When duration not specified, it's 1
        if ((years is None or year in years) and
            (durs is None or dur in durs)):
            return {'dir': m.group('dir'),
                'href': m.group('href'),
                'year': year,
                'dur': dur}
        else:
            return None
    else:
        return None

def state_filestub(st, is2005=False):
    """Given a 2-char abbreviation, return the state filestub (directory).

    The Census standard is the full state name, camel case, spaces
    removed. This generally is true for "United States" too, but in 2005
    they put a "0" in front of the name, to make sure it's sorted to the top.
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

class AcsServer(object):
    def __init__(self, baseurl, pums=False):
        self.baseurl = baseurl
        self.pums = pums

    def folders(self, years, durations):
        return get_links(self.baseurl, lambda href: acs_year_dur_filter(href, years, durations))

    def files_to_download(self, year, dur, states):
        # Get the year/dur URL on the server
        yd_url = self.year_dur_url(year, dur)

        if self.pums:
            r_url = yd_url + 'pums/'
        else:
            r_url = yd_url + 'summaryfile/'

        logger.debug("Requesting {0}".format(r_url))
        r = requests.get(r_url)
        logger.debug("Request returned {0}".format(r))

        if r.status_code == requests.codes.ok:
            # PUMS is easy
            if self.pums:
                return self.pums_files(r.url, year, dur, states)

            # For summary file, get a list of the links in that folder
            # In some years, each link represents a state. In others, there
            # is another layer we need to go into.
            links = get_links(r.url)

            if u'Alabama/' in links:
                # If the links contain state names (we use Alabama to check)
                # then, the files are organized in the old way.
                return self.old_sf_files(r.url, year, dur, states)
            else:
                return self.new_sf_files(r.url, year, dur, states)
        else:
            logger.warning("Invalid summaryfile directory for year=%s dur=%s rooturl=%s" % (year, dur, r.url))
            return r.status_code

    def year_dur_url(self, year, dur):
        """Return the URL to the folder on the server for an ACS year and duration.

        Args:
            year (int): Year of ACS
            dur (int): Duration of multiyear estimates. Note that, before 2007, 
                        all estimates were 1-year estimates

        Returns:
            The URL for the ACS data from a given year and estimate duration.

        """
        if year < 2007:
            return self.baseurl + 'acs{0}/'.format(year)
        else:
            return self.baseurl + 'acs{0}_{1}yr/'.format(year, dur)

    def pums_files(self, url, year, dur, states):
        '''Get list of PUMS files to download from the server.
        The returned list is actually a list of dicts, with entries for the
        folder portion of the url, the actual file name, and then the state
        abbreviation.
        '''
        files = []
                        
        for st in states:
            files.append({'url': url, 'file': 'unix_h%s.zip' % st, 'state': st})
            files.append({'url': url, 'file': 'unix_p%s.zip' % st, 'state': st})                 
        return files

    def old_sf_files(self, url, year, dur, states):
        '''Get list of files to download from the server, using the old system.
        The list is actually a list of dicts, with entries for the folder portion
        of the url, the actual file name, and the state abbreviation.
        
        The Census, in its infinite wisdom, has very inconsistent naming conventions,
        but the greatest difference is that before 2009, the summaryfile/ directory
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
        '''
        files = []

        for st in states:
            is2005 = (year==2005)
            logger.debug("State filestub: %s" % state_filestub(st, is2005))
            st_dir = url + state_filestub(st, is2005)
            st_links = get_links(st_dir)
            #print st_links
            
            if is2005:
                st_file = "all_{0}.zip".format(st)
                geo_file = "{0}geo.2005-1yr".format(st)
            elif "all_{0}.zip".format(st) in st_links:
                st_file = "all_{0}.zip".format(st)
                geo_file = "g{0}{1}{2}.txt".format(year, dur, st)
            elif "{0}_all_2006.zip".format(st) in st_links:
                st_file =  "{0}_all_2006.zip".format(st)
                geo_file = "g{0}{1}{2}.txt".format(year, dur, st)
            else:
                logger.warning("NO FILE for: {0} {1}".format(st, st_dir))
                continue
            
            files.append({'url': st_dir + '/', 'file': st_file, 'state': st})
            files.append({'url': st_dir + '/', 'file': geo_file, 'state': st})
        return files
        
    def new_sf_files(self, url, year, dur, states):
        """Get list of files to download from the server, using the new system.

        The returned list is actually a list of dicts, with entries for the
        folder portion of the url, the actual file name, and then the state
        abbreviation.
        
        Starting in 2009, the Census is more consistent with the structure of
        the directories. There is one subdirectory within summaryfile/ that
        contains all the state files, each of which is just a single zipped file.
        Each state does NOT, thus, have a subdirectory itself.
        """
        files = []
        
        if year==2009 and dur==1: # weird exception
            subdir = 'Entire_States/' 
        else:
            if dur == 1:
                # The subdirectory starts with the year covered.
                subdir = '{0}_ACSSF_By_State_All_Tables/'.format(year)
            else:
                # The subdirectory starts with the range of years covered
                start_yr = year - dur + 1
                subdir = '{0}-{1}_ACSSF_By_State_All_Tables/'.format(start_yr, year)
                
        for st in states:
            st_dir = url + subdir
            st_links = get_links(st_dir)
            for link in st_links:
                # look for the state abbreviation in any ZIP file
                if re.search(r'{0}.*\.zip'.format(state_filestub(st)), link):
                    files.append({'url': st_dir, 'file': link, 'state': st})
                    
        return files

class Local(object):
    """ Object representing local environment """
    def __init__(self, outdir, pums=False, overwrite=False):
        self.outdir = outdir
        self.pums = pums
        self.overwrite = overwrite

    @property
    def outdir(self):
        return self._outdir

    @outdir.setter
    def outdir(self, outdir):
        # Make sure directory exists. If not, create it.
        safe_make_dir(outdir)
        self._outdir = outdir

    def year_dur_destination(self, year, dur):
        """ Get year/dur path, and create it and subfolders if it doesn't exist. """
        yd_path = "{0}ACS{1}_{2}yr".format(self.outdir, year, dur)

        safe_make_dir(yd_path)
        if self.pums:
            safe_make_dir(yd_path + '/raw/zip')
            safe_make_dir(yd_path + '/clean')
        else:
            if dur == 5:
                for subdir in ("tracts", "nontracts"):
                    safe_make_dir("{0}/{1}/raw/zip".format(yd_path, subdir))
                    safe_make_dir("{0}/{1}/stubs".format(yd_path, subdir))
                    safe_make_dir("{0}/{1}/docs".format(yd_path, subdir))
                    safe_make_dir("{0}/{1}/code".format(yd_path, subdir))
            else:
                safe_make_dir(yd_path + '/raw/zip') # this is recursive, so it will create /raw and then /raw/zip
                safe_make_dir(yd_path + '/stubs')
                safe_make_dir(yd_path + '/docs')
                safe_make_dir(yd_path + '/code')

        return yd_path

    def destination_paths(self, year, dur, state, subdir=None):
        """ Return dict of destination paths for a year/dur/state. """
        yd_path = self.year_dur_destination(year, dur)
        state_filename = "%s_ACS%s_%syr.zip" % (state, year, dur)
        geo_filename = "g" + str(year) + str(dur) + str(state) + ".txt"

        if subdir is None:
            geo_path = '%s/raw/%s' % (yd_path, geo_filename)
            zip_path = '%s/raw/zip/%s' % (yd_path, state_filename)
        else:
            geo_path = '%s/%s/raw/%s' % (yd_path, subdir, geo_filename)
            zip_path = '%s/%s/raw/zip/%s' % (yd_path, subdir, state_filename)
        return {'yd_path': yd_path, 'state_filename': state_filename, 'geo_path': geo_path,
                'zip_path': zip_path}

    def download_files(self, files, year, dur):
        """ Download all the files in a file list. """
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for f in files:
                logger.debug("Trying to download {0}".format(f))
                url = "{url}{file}".format(url=f['url'], file=f['file'])
                __, filename = os.path.split(f['file'])
                fname, ext = os.path.splitext(filename)
                if ext.upper() == ".ZIP":
                    if fname.find("Not_Tracts_Block_Groups") >= 0:
                        subdir = 'nontracts'
                    elif fname.find("Tracts_Block_Groups_Only") >= 0:
                        subdir = 'tracts'
                    else:
                        subdir = None
                    path = self.destination_paths(year, dur, f['state'], subdir)['zip_path']
                else:
                    path = self.destination_paths(year, dur, f['state'])['geo_path']
                    # gets the filepath on the local system, where we download to

                if self.overwrite or not os.path.exists(path):
                    # If file does not already exist, then download it
                    logger.info("Downloading <{url}> to [{path}]".format(url=url, path=path))
                    #sys.stdout.flush()
                    future = executor.submit(download, url, path)
                    future.add_done_callback(self.download_callback)
                else:
                    logger.debug("NOT downloading: %s (already exists)" % path)

    def download_callback(self, future):
        '''This method is called after a file is finished downloading.
        It extracts the file that was downloaded.'''
        if future.exception() is not None:
            raise future.exception()
        else:
            r = future.result()
            logger.debug("DOWNLOAD CALLBACK; {0}".format(r))
            path = r['path']
            __, ext = os.path.splitext(path)
            root = os.path.split(path)[0]
            final_root = os.path.split(root)[0]
            if ext.upper() == ".ZIP":
                future = self.dl_executor.submit(self.extract_file, path, root, final_root)
                future.add_done_callback(self.extract_callback)

    def extract_callback(self, future):
        '''This method is called after a file has been extracted.'''
        print "Extract Callback"
        if future.exception() is not None:
            raise future.exception()
        else:
            r = future.result()
            print "EXTRACT CALLBACK: %s (%d files)" % (r['files'][0], len(r['files']))
            print "ORIGINAL: %s DIR: %s INTO: %s FINAL_INTO: %s" % (r['original'], r['dirs'][0], r['into'], r['final_into'])
            # Move files into root directory
            for i, f in enumerate(r['files']):
                src = "%s/%s" % (r['into'], f)
                src_name = os.path.split(src)[1] # get file name
                dst = "%s/%s" % (r['final_into'], src_name)
                '''NOTE: in certain years, the geo files are repeated in each
                sub-zip, but each one overwrites the previous one. Thus, there
                is only one copy in the /raw/zip/ folder at the end. Then, after the
                first subzip is processed, that one copy is moved into the /raw/ folder.
                Each subsequent copy will look for the geo file in /raw/zip/ and not find
                it, raising an error, which is why we don't try to move until checking
                if the file exists.'''
                if os.path.exists(src):
                    shutil.move(src, dst)
            # Then delete original
            os.remove(r['original'])
    
    def extract_file(self, path, into, final_into=None):
        """Extracts file at path to folder into. If final_into
        is specified, then the final files (after recursively unzipping
        everything) are moved into final_into."""
        
        print "EXTRACTING PATH:", path
        with zipfile.ZipFile(path, 'r') as z:
            # Extract all to d.root...
            z.extractall(into)
            # Then check to see if the files extracted contained more zip files!
            drc = ''

            extracted_files = []
            dirs = []
            for n in z.namelist():
                # Move file into root directory
                drc, fname = os.path.split(n)
                __, ext = os.path.splitext(fname)
                print fname, ext.upper()
                if ext.upper() == ".ZIP":
                    res = self.extract_file("%s/%s" % (into, n), into)
                    extracted_files.extend(res['files'])
                    dirs.extend(res['dirs'])
                else:
                    extracted_files.extend([n])
                    dirs.extend([drc])
            result = {'original': path, 'files': extracted_files, 'dirs': dirs, 'into': into, 'final_into': final_into}
            return result



#             return result

# def acs_folder(year, dur, rooturl='http://www2.census.gov/'):
#     """Return the folder on the server for an ACS year and duration.

#     Args:
#         year (int): Year of ACS
#         dur (int): Duration of multiyear estimates. Note that, before 2007, 
#                     all estimates were 1-year estimates
#         rooturl (Optional[str]): The base URL for the ACS files. The default
#                     should be fine unless the Census changes their URL
#                     structure.

#     Returns:
#         The URL for the ACS data from a given year and estimate duration.

#     """
#     if year < 2007:
#         return rooturl + 'acs{0}/'.format(year)
#     else:
#         return rooturl + 'acs{0}_{1}yr/'.format(year, dur)


# def state_folder(year, dur, st, mode='SF', rooturl='http://www2.census.gov/'):
#     """Return the folder on the server for an ACS year, duration, and state.

#     A folder consists of the root URL, plus the ACS folder for a year/
#     duration, plus some standard subdirectories, and then possibly a state
#     subdirectory.


#     """
#     if year < 2007:
#         folder = rooturl + 'acs{0}/'.format(year)
#     else:
#         folder = rooturl + 'acs{0}_{1}yr/'.format(year, dur)

#     # For PUMS, all same subfolder
#     if mode == "PUMS":
#         return folder + 'pums/'

#     # Otherwise:


# def state_filestub(st, is2005=False):
#     """Return the Census file stub (directory or filename) for a state.

#     File stubs refer to a string that the Census uses both as a directory
#     and as the filename (not including file extension).

#     The Census standard is the full state name, camel case, spaces
#     removed. This generally is true for "United States" too, but in 2005
#     they put a "0" in front of the name, to make sure it's sorted to the top.

#     Args:
#         st: 2-character abbreviation
#         is2005 (Optional): whether year is 2005

#     Returns:
#         A string with the state's directory name

#     >>> state_filestub('ny')
#     u'NewYork'

#     >>> state_filestub('us')
#     u'UnitedStates'

#     >>> state_filestub('us', is2005=True)
#     u'0UnitedStates'

#     >>> state_filestub('qq')
#     Exception
#     ...
#     """
#     state = us.states.lookup(st)
#     if state is None:
#         if st.upper() == "US":
#             if is2005:
#                 return u"0UnitedStates"
#             else:
#                 return u"UnitedStates"
#     else:
#         return state.name.replace(" ", "")


# ######################################
# #### GET REMOTE FILE LISTS        ####
# ######################################
# def get_acs_files(year, dur, states,
#                   mode="SF", rooturl='http://www2.census.gov/'):
#     """Get list of files to download from server.

#     The returned list is actually a list of dicts, with entries for the
#     folder portion of the url, the actual file name, and then the state
#     abbreviation.

#     Args:
#         year: the ACS year (the last year for multiyear estimates)
#         dur: the ACS multiyear duration (1, 3, or 5)
#         states (List[str]): a list of 2-letter state abbreviations (strings)
#         mode (Optional): summary file ("SF") or PUMS ("PUMS"). Defaults to "SF"
#         rooturl (Optional): the root URL. Defaults to 'http://www2.census.gov/'

#     Returns:
#         A list of dicts, where each dict represents a single file and has:
#             'folder': the URL of the folder containing the file
#             'file': the file name, including extension
#             'state': the 2-letter abbreviation of the state

#     Examples:
#         In 2009 and after, the summary file is pretty standard

#         >>> import pprint
#         >>> get_acs_files(year=2009, dur=1, states=['NY', 'US'], mode='SF')
#         ... #
#         [{'folder': u'http://www2.census.gov/acs2009_1yr/summaryfile/Entire_States/',
#             'file': u'NewYork.zip', 'state': 'NY'},
#         {'folder': u'http://www2.census.gov/acs2009_1yr/summaryfile/Entire_States/',
#             'file': u'UnitedStates.zip', 'state': 'US'}]


#         In 2005, the US folder has a "0" at the beginning. Note the different names
#         for the files, as well as state-specific folders on the server.

#         >>> get_acs_files(year=2005, dur=1, states=['MA', 'US'], mode='SF')
#         ... #
#         [{'folder': u'http://www2.census.gov/acs2005/summaryfile/Massachusetts/',
#             'file': u'all_ma.zip', 'state': 'MA'},
#         {'folder': u'http://www2.census.gov/acs2005/summaryfile/0UnitedStates/',
#             'file': u'all_us.zip', 'state': 'US'}]


#         In 2006, the file names are different.
#         >>> get_acs_files(year=2006, dur=1, states=['NJ', 'US'], mode='SF')
#         [{'folder': u'http://www2.census.gov/acs2006/summaryfile/NewJersey/',
#             'file': u'nj_all_2006.zip', 'state': 'NJ'},
#         {'folder': u'http://www2.census.gov/acs2006/summaryfile/UnitedStates/',
#             'file': u'us_all_2006.zip', 'state': 'US'}]

#         Multiyear estimates example
#         >>> get_acs_files(year=2013, dur=5, states=['NY', 'US'], mode='SF')
#         None

#         PUMS example.
#         >>> get_acs_files(year=2009, dur=1, states=['NY', 'US'], mode='PUMS')
#         None



#     """
#     if mode == "PUMS":
#         # For PUMS, just return the list of person and household files
#         return [{'url': url,
#                  'file': 'unix_%s%s.zip' % (rectype, st),
#                  'state': st}
#                 for rectype in ('h', 'p')
#                 for st in states]

#     else:  # Summary File has weird standards
#         # Get state directory from year, dur, state
#         return get_files_new_SF(url, year, dur, states)


# def get_files_new_SF(url, year, dur, states):
#     """Get remote files using new SF standard.

#     Starting in 2009, the Census is more consistent with the structure of
#     the directories. There is one subdirectory within summaryfile/ that
#     contains all the state files, each of which is just a single zipped file.
#     Each state does NOT, thus, have a subdirectory itself.

#     >>> get_files_new_SF('http://www2.census.gov/acs2009_1yr/summaryfile', 2009, 1, ['ny'])
#     None

#     """
#     # Start with empty list of files
#     files = []

#     # Set subdirectory based on year and duration
#     if year == 2009 and dur == 1:  # weird exception
#         subdir = 'Entire_States/'
#     elif year != 2009 and dur == 1:  # single-year estimates except 2009
#         # The subdirectory starts with the year covered.
#         subdir = '%s_ACSSF_By_State_All_Tables/' % year
#     else:  # Multiyear estimates
#         # The subdirectory starts with the range of years covered
#         start_yr = year - dur + 1
#         subdir = '%s-%s_ACSSF_By_State_All_Tables/' % (start_yr, year)

#     # Return list of files in subdirectory for each state
#     # Only want zip files
#     for st in states:
#         st_links = get_links(url + subdir)
#         for link in st_links:
#             if re.search(r'%s.*\.zip' % get_state_dir(st), link):
#                 files.append({'url': st_dir, 'file': link, 'state': st})
#     return files


# def get_files_old_SF(url, year, dur, states):
#     """Get remote file list using old SF standard.

#     The Census, in its infinite wisdom, has very inconsistent naming conventions,
#     but the greatest difference is that, before 2009, the summaryfile/ directory
#     contains a subdirectory for each state, and within those subdirectories
#     there is a listing of all the files as well as a zip file containing all
#     those files. Thus the format is generally (with some exceptions):

#     acsYEAR_DURyr/summaryfile/StateName/all_st.zip

#     Where StateName is what is returned by get_state_dir(), basically
#     the state name in camel case and without spaces, and st is the two-letter
#     abbreviation (lowercase) for that state (or "us"). In 2005 and 2006, the outermost
#     directory is just acsYEAR, without any duration (and those are both 1-year files).
#     In 2006, moreover, the name of the actual zip files is different:
#         st_all_2006.zip


#     """
#     # Start with empty list of files
#     files = []

#     for st in states:
#         is2005 = (year == 2005)
#         st_dir = url + get_state_dir(st, is2005)
#         st_links = get_links(st_dir)

#         if is2005:
#             st_file = "all_%s.zip" % st
#             geo_file = "%sgeo.2005-1yr" % st
#         elif "all_%s.zip" % st in st_links:
#             st_file = "all_%s.zip" % st
#             geo_file = "g%s%s%s.txt" % (year, dur, st)
#         elif "%s_all_2006.zip" % st in st_links:
#             st_file = "%s_all_2006.zip" % st
#             geo_file = "g%s%s%s.txt" % (year, dur, st)
#         else:
#             print "NO FILE: %s" % st, st_dir
#             break

#         files.append({'url': st_dir + '/', 'file': st_file, 'state': st})
#         files.append({'url': st_dir + '/', 'file': geo_file, 'state': st})
#     return files


# class CensusDownloader(object):

#     """Class to hold downloader context.

#     """

#     def __init__(self, baseurl, 
#                     years, durations, states):
#         """Init method"""
#         self.baseurl = baseurl
#         self.years = years
#         self.durations = durations
#         self.states = states

        #self.debug = debug
        #self.verbose = verbose
        #self.outdir = outdir
        #self.link_filter = link_filter
        #self.mode = mode

    # @property
    # def outdir(self):
    #     return self._outdir

    # @outdir.setter
    # def outdir(self, outdir):
    #     # Make sure directory exists. If not, create it.
    #     try:
    #         os.makedirs(outdir)
    #     except OSError:
    #         # If directory already exists, fine
    #         # otherwise, a real error, so raise it
    #         if not os.path.isdir(outdir):
    #             raise
    #     self._outdir = outdir

    # @property
    # def link_filter(self):
    #     return self._link_filter

    # @property
    # def remote_files(self):
    #     if self._remote_files is None:
    #         folders = get_links(self.baseurl, self.link_filter)

    #     return self._remote_files

    # @property
    # def dest_files(self):
    #     return self._dest_files

    # def download(self):
    #     """Download remote files to destination.

    #     """
    #     for f in self.remote_files:
    #         download(url, path)


@click.group()
@click.option('--debug/--no-debug', default = False)
@click.option('--verbose/--no-verbose', '-v/-no-v', default=False)
@click.option('--log', '-l', help="Log to file path", type=click.Path(writable=True))
#@click.pass_context
def dl_acs(debug, verbose, log): #, baseurl, startyear, endyear, durs, states, debug, verbose):
    """Main ACS Download comand"""
    # Set up CensusDownloader object
    # click.echo(ctx)
    # years = range(startyear, endyear+1)
    # durations = (str(dur) for dur in durs)
    #chromalog.basicConfig(format="%(levelname)s: %(funcName)s:%(lineno)d -- ")
    log_format = "%(levelname)-10s:%(funcName)16s:%(lineno)-5d -- %(message)s"
    if log is not None:
        chromalog.basicConfig(filename=log, filemode='w', format=log_format)
    else:
        chromalog.basicConfig(format=log_format)

    

    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    #ctx.obj = CensusDownloader(baseurl,years, durations, states)
    if debug:
        #click.echo("Debugger on")
        logger.debug("Debugger On")


@dl_acs.command()
#@click.option('--years', '-y', nargs=2, type=click.INT, multiple=True)
#@click.option('--states', '-s')
#@click.argument('outdir')
@click.option('--startyear', '-s', type=click.INT, prompt=True)
@click.option('--endyear', '-e', type=click.INT, prompt=True)
@click.option('--durs', '-d', type=click.Choice(['1', '3', '5']), multiple=True, prompt=True)
@click.option('--outdir','-o', help="Directory in which to store output", prompt=True)
@click.option('--overwrite/--no-overwrite', default=False)
@click.option('--baseurl',
              default='http://www2.census.gov/',
              help="Census root URL")
@click.argument('states', default='us', nargs=-1)
#@click.pass_context
def sf(states, baseurl, startyear, endyear, durs, overwrite, outdir):
    """Download Summary File datafiles"""
    logger.critical("Downloading")
    click.echo("Downloading SF")
    #logger = logging.getLogger()
    #click.echo(ctx.years)
    acs = AcsServer(baseurl)
    local = Local(outdir, pums=False)


    years = range(startyear, endyear+1)
    durations = [int(dur) for dur in durs]
    logger.debug("Years: {0}".format(years))
    logger.debug("Durations: {0}".format(durations))

    for year in years:
        for dur in durations:
            # Check for invalid combinations
            if (year <= 2006 and dur != 1) or (year <= 2008 and dur == 5) or (year > 2013 and dur == 3):
                logger.info("Skipping invalid year/duration combination: {0} {1}-year".format(year, dur))
                continue


            #rooturl = acs.year_dur_url(year, dur)

             # Limit states to those where zip files don't still exist, unless overwrite
            new_states = [s for s in states if overwrite or not
                            os.path.exists(local.destination_paths(year, dur, s)['zip_path'])]
            if len(new_states) == 0:
                logger.info("Skipping {year} {dur}-year: All states already downloaded ({states})".format(year=year, dur=dur, states=states))

            logger.debug("{0} {1}-year: {2}".format(important(year), important(dur), new_states))
            #logger.debug("New States: {0}".format(new_states))

            remote_files = acs.files_to_download(year, dur, new_states)
            logger.debug("Files to download: \n{0}".format(pprint.pprint(remote_files)))

            local.download_files(remote_files, year, dur)
            logger.info("%s\n%s" % (success("Files:"), pprint.pprint(remote_files)))
            # Get file list based on PUMS/SF and year

            # Download files in list


    #folders = get_links(baseurl, lambda href: acs_year_dur_filter(href, years, durations))
    # mode = "SF"
    # click.echo(acs.folders)
    # for folder in acs.folders:
    #     # The 'dir' of the folder is the year/duration directory on the Census server
    #     rooturl = acs.baseurl + folder['dir'] + '/'
    #     new_states = [s for s in states if not 
    #                         os.path.exists(local.destination_paths(folder['year'], folder['dur'], s)['zip_path'])]

    #     links = get_links(rooturl)
    #     if 'Alabama/' in links:
    #         files = get_old_files
    #     else:
    #         files = get new files

    #     server.download(files, year, dur)

    #get_files_new_SF(url, year, dur, states)


@dl_acs.command()
def pums():
    """Download Public Use Microdata Sample datafiles"""
    click.echo("Downloading PUMS")
