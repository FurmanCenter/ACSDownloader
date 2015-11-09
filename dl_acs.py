import os
import click
import shutil
import logging
#import pprint
from colorama import Fore, Back, Style
from functools import partial
#from colorama import init as colorama_init
#from termcolor import colored


# Make termcolor work on Windows
#colorama_init()
import chromalog
from chromalog.mark.helpers.simple import important, success
logger = logging.getLogger(__name__)

fh = logging.FileHandler('dl_acs.log', mode='w')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

# for handler in logging.root.handlers:
#     logger.debug(handler)
#     handler.addFilter(logging.Filter(__name__))
#logging.critical("TEST CHROMALOG")
#logger.critical("Testing Chromalog")









####################################################
####################################################
#
#                       LOCAL
#
####################################################
####################################################




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
    #log_format = "%(levelname)-10s:%(funcName)16s:%(lineno)-5d -- %(message)s"
    log_format = "%(levelname)s:%(lineno)-5d: %(message)s"
    
    if log is not None:
        #chromalog.basicConfig(filename=log, filemode='w', format=log_format)
        logging.basicConfig(filename=log, filemode='w', format=log_format)
    else:
        #chromalog.
        logging.basicConfig(format=log_format)

    

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
@click.option('--dryrun/--no-dryrun', help="Don't download files, just get list of files", default=False, is_flag=True)
@click.option('--startyear', '-s', type=click.INT, prompt=True)
@click.option('--endyear', '-e', type=click.INT, prompt=True)
@click.option('--durs', '-d', type=click.Choice(['1', '3', '5']), multiple=True, prompt=True)
@click.option('--outdir','-o', type=click.Path(file_okay=False, writable=True), help="Directory in which to store output", prompt=True)
@click.option('--overwrite/--no-overwrite', default=False)
@click.option('--baseurl',
              help="Census root URL")
@click.argument('states', default='us', nargs=-1)
#@click.pass_context
def sf(states, baseurl, startyear, endyear, durs, overwrite, outdir, dryrun):
    """Download Summary File datafiles"""
    logger.critical("Downloading")
    click.echo("Downloading SF")
    #logger = logging.getLogger()
    #click.echo(ctx.years)


    years = range(startyear, endyear+1)
    durations = [int(dur) for dur in durs]


    logger.debug("Years: {0}".format(years))
    logger.debug("Durations: {0}".format(durations))

    acs = AcsServer(baseurl=baseurl, years=years, durs=durations, pums=False)
    local = Local(outdir, overwrite=overwrite, pums=False)

    # Get list of files to download
    # Get list of data files
    # Get list of documentation
    # Download them
    # Extract downloads
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

            logger.info(Fore.GREEN + Style.BRIGHT + "{0} {1}-year: {2}".format(year, dur, new_states) + Fore.RESET + Style.RESET_ALL)
            #logger.debug("New States: {0}".format(new_states))

            state_data_files = acs.state_data_files(year, dur, new_states)
            logger.debug("Data files to download: \n{0}{1}{2}".format(Fore.MAGENTA, pprint.pformat([str(f['url']).replace(acs.urlroot, "") for f in state_data_files]), Fore.RESET))

            stubs_and_doc_files = acs.stubs_and_documentation(year, dur)

            logger.debug("Documentation files to download: \n{0}{1}{2}".format(Fore.GREEN, pprint.pformat(stubs_and_doc_files), Fore.RESET))
            #remote_files = acs.files_to_download(year, dur, new_states)
            #logger.debug(pprint.pformat(remote_files))
            #logger.debug("Files to download: \n{0}{1}{2}".format(Fore.MAGENTA, pprint.pformat([str(f['url'] + f['file']).replace(acs.urlroot, "") for f in [filesets for filesets in remote_files]]), Fore.RESET))

            if not dryrun:
                local.download_data_files(state_data_files, year, dur)
                local.download_stubs_and_docs(stubs_and_doc_files, year, dur)
            #logger.info("%s\n%s" % (success("Files:"), pprint.pformat(remote_files)))
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


# @dl_acs.command()
# def pums():
#     """Download Public Use Microdata Sample datafiles"""
#     click.echo("Downloading PUMS")
