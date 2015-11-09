import os
import requests
from bs4 import BeautifulSoup as bs
import click
import re
import shutil
import us
import logging
import pprint
from colorama import Fore, Back, Style
from functools import partial
import zipfile
#from colorama import init as colorama_init
#from termcolor import colored

import concurrent.futures

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





class AcsServer(object):
    def __init__(self, years, durs=[1, 3, 5], rooturls = None, baseurl=None, pums=False):
        """ statesurl is a dict of durations """
        self.pums = pums
        self.durs = durs
        self.years = years
        self.urlroot = baseurl #self.urlroot(baseurl)
        self.rooturls = rooturls

        logger.info("Created States URLS: \n%s" % pprint.pformat(self.rooturls))

    @property
    def urlroot(self):
        return self._urlroot

    @urlroot.setter
    def urlroot(self, baseurl):
        if baseurl is not None:
            self._urlroot = baseurl
        else:
            if self.pums:
                self._urlroot = "http://www2.census.gov/programs-surveys/acs/data/pums"
            else:
                self._urlroot = "http://www2.census.gov/programs-surveys/acs/summary_file"

    @property
    def rooturls(self):
        return self._rooturls

    @rooturls.setter
    def rooturls(self, user_rooturls):
        """ Set the URL for the """
        logger.debug("Initializing Root URLs")
        if user_rooturls:
            logger.debug("Replacing root urls from user: %s" % pprint.pprint(user_rooturls))
            self._rooturls = user_rooturls
        else:
            rooturls = {}
            for year in self.years:
                for dur in self.durs:  
                    dataurl = None
                    docurl = None
                    if self.pums:
                        if year <= 2006 and dur == 1:
                            dataurl = "{root}/{year}/".format(root=self.urlroot, year=year)
                        elif (year <= 2008 and dur in [1, 3]) or (year >= 2009 and dur in [1, 3, 5]):
                            dataurl = "{root}/{year}/{dur}-Year/".format(root=self.urlroot, year=year, dur=dur)
                        else:
                            continue
                    else:
                        # Data URL
                        if year <= 2006 and dur == 1:
                            dataurl = "{root}/{year}/data/".format(root=self.urlroot, year=year)
                        elif year <= 2008 and dur in [1, 3]:
                            dataurl = "{root}/{year}/data/{dur}_year/".format(root=self.urlroot, year=year, dur=dur)
                        # elif year == 2009 and dur == 1:
                        #     # Weird exception
                        #     dataurl = "{root}/{year}/data/{dur}_year-all-states/".format(root=self.urlroot, year=year, dur=dur)
                        elif year >= 2009 and dur in [1, 3, 5]:
                            dataurl = "{root}/{year}/data/{dur}_year_by_state/".format(root=self.urlroot, year=year, dur=dur)
                        else:
                            continue
                        
                        # Documentation URL
                        if year <= 2006 or year >= 2013:
                            docurl = "{root}/{year}/documentation/".format(root=self.urlroot, year=year)
                        elif year <= 2012:
                            docurl = "{root}/{year}/documentation/{dur}_year/".format(root=self.urlroot, year=year, dur=dur)

                    # Test for validity of data URL
                    if valid_url(dataurl):
                        logger.debug("Valid data root url ({year}/{dur}-year): {url}".format(year=year, dur=dur, url=dataurl))
                        if year in rooturls:
                            rooturls[year][dur] = { 'data': dataurl, 'documentation': docurl }
                        else:
                            rooturls[year] = { dur: { 'data': dataurl, 'documentation': docurl } }
                    else:
                        logger.warning("Invalid data root url ({year}/{dur}-year): {url}".format(year=year, dur=dur, url=dataurl))
                        # if year in rooturls:
                        #     rooturls[year][dur] = { 'data': None, 'documentation': None }
                        # else:
                        #     rooturls[year] = { dur: { 'data': None, 'documentation': None } }
            self._rooturls = rooturls

    def documentation_rooturls(self):
        logger.debug("Initializing Documentation URLs")


    def folders(self, years, durations):
        return get_links(self.baseurl, lambda href: acs_year_dur_filter(href, years, durations))


    def state_data_files(self, year, dur, states):
        try:
            state_urls = get_links(self.rooturls[year][dur]['data'])
        except KeyError:
            logger.error("No valid data URL for {year}, {dur}".format(year=year, dur=dur))
            return []

        data_files = []

        if self.pums:
            pass
        else:
            if u'Alabama/' in state_urls:
                # Old SF
                return self.old_sf_files(year, dur, states)
            else:
                # New SF
                return self.new_sf_files(year, dur, states)



    def stubs_and_documentation(self, year, dur):
        try:
            doc_url = self.rooturls[year][dur]['documentation']
        except KeyError:
            logger.error("No valid documentation URL for {year}, {dur}".format(year=year, dur=dur))
            return { 'stubs': [], 'docs': [], 'macro': [] }


        # Technical documentation PDF file
        tech_doc_re = re.compile(r'(.*_SF_Tech_Doc\.pdf)')
        def _tech_filter(href):
            if tech_doc_re.search(href):
                return href

        tech_doc = get_links(doc_url, link_filter = _tech_filter  )
        logger.debug("Tech doc: %s" % tech_doc)
        docs = [{ 'url': doc_url + tdoc, 'file': tdoc } for tdoc in tech_doc]

        # Stubs file
        old_stub_re = re.compile(r'merge_5_6.*')
        new_stub_re = re.compile(r'Sequence_?Number_?Table_?Number_?Lookup.*')
        dur_stub_re = re.compile(r'ACS_' + re.escape(str(dur)) + r'yr_Seq_Table_Number_Lookup.*')
        #logger.debug(pprint.pformat(get_links(doc_url)))

        # Filter for old and new stub files
        def _match_old_or_new(url):
            if old_stub_re.search(url) or new_stub_re.search(url) or dur_stub_re.search(url):
                return url
            else:
                return None
            # old = old_stub_re.search(url)
            # if old:
            #     return old
            # new = new_stub_re.search(url)
            # if new:
            #     return new
            # return dur_stub_re.search(url)

        if year==2005:
            # 2005 stubs were not moved to new server
            stub_urls = ["http://www2.census.gov/acs2005/Chapter_6_acs_2005_tables_Sum_file_shells.xls"]
            #stubs = [{ 'url': "http://www2.census.gov/acs2005/",
            #            'file': "Chapter_6_acs_2005_tables_Sum_file_shells.xls" }]
        elif year == 2006:
            stub_urls = ["http://www2.census.gov/acs2006/merge_5_6_final.txt", "http://www2.census.gov/acs2006/merge_5_6_final.xls" ]
            # stubs = [{ 'url': "http://www2.census.gov/acs2006/",
            #             'file': "merge_5_6_final.txt" },
            #         { 'url': "http://www2.census.gov/acs2006/",
            #         'file': "merge_5_6_final.xls" }] 
        elif year == 2007:
            stub_files = get_links(doc_url, link_filter=_match_old_or_new)
            stub_urls = [doc_url + f for f in stub_files]
            #tubs = [{ 'url': doc_url, 'file': f } for f in stub_files]
        elif year <= 2012:
            stub_files = get_links(doc_url + "user_tools/", link_filter=_match_old_or_new)
            stub_urls = [doc_url + "user_tools/" + f for f in stub_files]
            #stubs = [{ 'url': doc_url + "user_tools/", 'file': f } for f in stub_files]
        elif year >= 2013:
            stub_files = get_links(doc_url + "user_tools/", link_filter=_match_old_or_new)
            stub_urls = [doc_url + "user_tools/" + f for f in stub_files]

        stubs = [{ 'url': u } for u in stub_urls ]

        # Example Macros
        if year<=2006:
            macro_url = None
        elif year==2007 and dur==3:
            macro_url = "http://www2.census.gov/programs-surveys/acs/summary_file/2007/documentation/3_year/Sample SAS Programs/summary_file_example_macros.sas"
        elif year <= 2008:
            macro_url = doc_url + "0SASExamplePrograms/summary_file_example_macros.sas"
        elif year==2009 and dur==3:
            macro_url = "http://www2.census.gov/programs-surveys/acs/summary_file/2009/documentation/3_year/user_tools/SF_ALL_Macro.sas"
        elif year <= 2012:
            macro_url = doc_url + "user_tools/SF_All_Macro.sas"
        elif year == 2013:
            macro_url = doc_url + "user_tools/SummaryFile_All_Macro.sas"
        elif year == 2014:
            macro_url = doc_url + "user_tools/SF_All_Macro_1YR.sas"

        macros = None
        if macro_url:
            macros = [{ 'url': macro_url }]

        # """
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2007/documentation/1_year/0SASExamplePrograms/summary_file_example_macros.sas
                   
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2008/documentation/1_year/0SASExamplePrograms/summary_file_example_macros.sas
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2008/documentation/3_year/0SASExamplePrograms/summary_file_example_macros.sas
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2009/documentation/1_year/user_tools/SF_All_Macro.sas
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2009/documentation/3_year/user_tools/SF_ALL_Macro.sas
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2009/documentation/5_year/user_tools/SF_All_Macro.sas
        #             http://www2.census.gov/programs-surveys/acs/summary_file/2010/documentation/1_year/user_tools/SF_All_Macro.sas"""
        logger.debug("STUBS: \n%s" % pprint.pformat(stubs))

        return { 'stubs': stubs, 'docs': docs, 'macros': macros }

    def files_to_download(self, year, dur, states):
        # Get the year/dur URL on the server
        datafiles = self.state_data_files(year, dur, states)
        stubs_and_docs = self.stubs_and_documentation(year, dur)
        return { 'data': datafiles,
                'stubs': stubs_and_docs['stubs'],
                'docs': stubs_and_docs['docs'],
                'macro': stubs_and_docs['macro'] }
        # yd_url = self.year_dur_url(year, dur)

        # if self.pums:
        #     r_url = yd_url + 'pums/'
        # else:
        #     r_url = yd_url + 'summaryfile/'

        # logger.debug("Requesting {0}".format(r_url))
        # r = requests.get(r_url)
        # logger.debug("Request returned {0}".format(r))

        # if r.status_code == requests.codes.ok:
        #     # PUMS is easy
        #     if self.pums:
        #         return self.pums_files(r.url, year, dur, states)

        #     # For summary file, get a list of the links in that folder
        #     # In some years, each link represents a state. In others, there
        #     # is another layer we need to go into.
        #     links = get_links(r.url)

        #     if u'Alabama/' in links:
        #         # If the links contain state names (we use Alabama to check)
        #         # then, the files are organized in the old way.
        #         return self.old_sf_files(r.url, year, dur, states)
        #     else:
        #         return self.new_sf_files(r.url, year, dur, states)
        # else:
        #     logger.warning("Invalid summaryfile directory for year=%s dur=%s rooturl=%s" % (year, dur, r.url))
        #     return r.status_code

    # def year_dur_url(self, year, dur, urltype="data"):
    #     """Return the URL to the folder on the server for an ACS year and duration.

    #     Args:
    #         year (int): Year of ACS
    #         dur (int): Duration of multiyear estimates. Note that, before 2007, 
    #                     all estimates were 1-year estimates

    #     Returns:
    #         The URL for the ACS data from a given year and estimate duration.

    #     """
    #     if urltype == "data":
    #         if self.pums:
    #             if year < 2007:
    #                 return "{root}/{year}/".format(root=self.urlroot, year=year)
    #             else:
    #                 return "{root}/{year}/{dur}-Year/".format(root=self.urlroot, year=year, dur=dur)
    #         else:
    #             if year <= 2006:
    #                 return "{root}/{year}/data/".format(root=self.urlroot, year=year)
    #             elif year <= 2008:
    #                 return "{root}/{year}/data/{dur}_year/".format(root=self.urlroot, year=year, dur=dur)
    #             elif year == 2009 and dur == 1:
    #                 # Weird exception
    #                 return "{root}/{year}/data/{dur}_year-all-states/".format(root=self.urlroot, year=year, dur=dur)
    #             else:
    #                 return "{root}/{year}/data/{dur}_year_by_states/".format(root=self.urlroot, year=year, dur=dur)
    #     elif urltype == "documentation":
    #         if self.pums:
    #             pass
    #         else:
    #             if year <= 2006 or year >= 2013:
    #                 return "{root}/{year}/documentation/".format(root=self.urlroot, year=year)
    #             elif year <= 2012:
    #                 return "{root}/{year}/documentation/{dur}_year/".format(root=self.urlroot, year=year, dur=dur)
               


    def pums_files(self, url, year, dur, states):
        '''Get list of PUMS files to download from the server.
        The returned list is actually a list of dicts, with entries for the
        folder portion of the url, the actual file name, and then the state
        abbreviation.
        '''
        files = []
                        
        for st in states:
            #files.append({'url': url, 'file': 'unix_h%s.zip' % st, 'state': st})
            #files.append({'url': url, 'file': 'unix_p%s.zip' % st, 'state': st})                 
            files.append({'url': url + 'unix_h%s.zip' % st, 'state': st})
            files.append({'url': url + 'unix_p%s.zip' % st, 'state': st})      
        return files

    def old_sf_files(self, year, dur, states):
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
            st_dir = self.rooturls[year][dur]['data'] + state_filestub(st, is2005)
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
            
            #files.append({'url': st_dir + '/', 'file': st_file, 'state': st})
            #files.append({'url': st_dir + '/', 'file': geo_file, 'state': st})
            files.append({'url': st_dir + '/' + st_file, 'state': st })
            files.append({'url': st_dir + '/' + geo_file, 'state': st })
            
        return files
        
    def new_sf_files(self, year, dur, states):
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
          
        for st in states:
            st_dir = self.rooturls[year][dur]['data']
            st_links = get_links(st_dir)
            for link in st_links:
                # look for the state name in any ZIP file
                if re.search(r'{0}.*\.zip'.format(state_filestub(st)), link):
                    #files.append({'url': st_dir, 'file': link, 'state': st})
                    files.append({ 'url': st_dir + link, 'state': st })
                    
        return files



####################################################
####################################################
#
#                       LOCAL
#
####################################################
####################################################
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
        logger.debug("YEAR/DUR destination {}: {}".format(self.pums, yd_path))
        if self.pums:
            safe_make_dir(os.path.join(yd_path, 'raw', 'zip'))
            safe_make_dir(os.path.join(yd_path,'clean'))
        else:
            # Create raw file, and subdirectories if it's 5 year
            if int(dur) == 5:
                for subdir in ("tracts", "nontracts"):
                    safe_make_dir(os.path.join(yd_path, 'raw', subdir, 'zip'))
            else:
                safe_make_dir(os.path.join(yd_path, 'raw', 'zip'))

            logger.debug("Making directories %s" % yd_path)
            safe_make_dir(os.path.join(yd_path, 'stubs')) #yd_path + '/stubs')
            safe_make_dir(os.path.join(yd_path, 'docs')) #yd_path + '/docs')
            safe_make_dir(os.path.join(yd_path, 'code')) #yd_path + '/code')
            assert os.path.isdir(os.path.join(yd_path, 'code'))

            # if dur == 5:
            #     for subdir in ("tracts", "nontracts"):
            #         safe_make_dir(os.path.join(yd_path, 'raw', subdir, 'zip')) #"{0}/raw/{1}/zip".format(yd_path, subdir))
            #     safe_make_dir(os.path.join(yd_path, 'stubs')) #"{0}/stubs".format(yd_path))
            #     safe_make_dir(os.path.join(yd_path, 'docs')) #"{0}/docs".format(yd_path))
            #     safe_make_dir(os.path.join(yd_path, 'code')) #"{0}/code".format(yd_path))
            # else:
            #     safe_make_dir(os.path.join(yd_path, 'raw', 'zip')) #yd_path + '/raw/zip') # this is recursive, so it will create /raw and then /raw/zip
            #     safe_make_dir(os.path.join(yd_path, 'stubs')) #yd_path + '/stubs')
            #     safe_make_dir(os.path.join(yd_path, 'docs')) #yd_path + '/docs')
            #     safe_make_dir(os.path.join(yd_path, 'code')) #yd_path + '/code')

        return yd_path

    def destination_paths(self, year, dur, state, subdir=None):
        """ Return dict of destination paths for a year/dur/state. """
        yd_path = self.year_dur_destination(year, dur)
        state_filename = "%s_ACS%s_%syr.zip" % (state, year, dur)
        geo_filename = "g" + str(year) + str(dur) + str(state) + ".txt"

        if subdir is None:
            geo_path = os.path.join(yd_path, 'raw', geo_filename) #'%s/raw/%s' % (yd_path, geo_filename)
            zip_path = os.path.join(yd_path, 'raw', 'zip', state_filename) #'%s/raw/zip/%s' % (yd_path, state_filename)
        else:
            geo_path = os.path.join(yd_path, 'raw', subdir, geo_filename) #'%s/raw/%s/%s' % (yd_path, subdir, geo_filename)
            zip_path = os.path.join(yd_path, 'raw', subdir, 'zip', state_filename) #'%s/raw/%s/zip/%s' % (yd_path, subdir, state_filename)
        return {'yd_path': yd_path, 'state_filename': state_filename, 'geo_path': geo_path,
                'zip_path': zip_path}

    def download_data_files(self, files, year, dur):
        """ Download all the files in a file list. """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for f in files:
                logger.debug("Trying to download {0}".format(f))
                #url = "{url}{file}".format(url=f['url'], file=f['file'])
                __, filename = os.path.split(f['url'])
                fname, ext = os.path.splitext(filename)
                if fname.find("Not_Tracts_Block_Groups") >= 0:
                    subdir = 'nontracts'
                elif fname.find("Tracts_Block_Groups_Only") >= 0:
                    subdir = 'tracts'
                else:
                    subdir = None

                logger.debug("Filename: {}".format(filename))
                logger.debug("Fname: {}".format(fname))
                logger.debug("ext: {}; upper: {}; == {}".format(ext, ext.upper(), (ext.upper()==".ZIP")))
                logger.debug("subdir: {}".format(subdir))
                # If zip file, use zip path; otherwise, it's the geo file

                dest_path = self.destination_paths(year, dur, f.get('state'), subdir)
                logger.debug(dest_path)
                if ext.upper() == ".ZIP":
                    path = self.destination_paths(year, dur, f.get('state'), subdir)['zip_path']
                else:
                    path = self.destination_paths(year, dur, f.get('state'), subdir)['geo_path']
                    # gets the filepath on the local system, where we download to

                if self.overwrite or not os.path.exists(path):
                    # If file does not already exist, then download it
                    logger.info("Downloading <{url}> to [{path}]".format(url=f['url'], path=path))
                    #sys.stdout.flush()
                    future = executor.submit(download, f['url'], path)
                    future.add_done_callback(self.download_callback)
                else:
                    logger.debug("NOT downloading: %s (already exists)" % path)

    def download_stubs_and_docs(self, files, year, dur):
        #with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        logger.debug("Dowloading docs: {}".format(files))
        if files.get('docs'):
            for d in files.get('docs'):
                __, fname = os.path.split(d['url'])
                path = os.path.join(self.year_dur_destination(year, dur), 'docs', fname)

                download(d['url'], path)

        if files.get('stubs'):
            for s in files.get('stubs'):
                __, fname = os.path.split(s['url'])
                path = os.path.join(self.year_dur_destination(year, dur), 'stubs', fname)
                download(s['url'], path)

        if files.get('macros'):
            for m in files.get('macros'):
                logger.debug("MACROS: %s" % m)
                __, fname = os.path.split(m['url'])
                path = os.path.join(self.year_dur_destination(year, dur), 'code', fname)
                download(m['url'], path)


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
            # If a zip file, extract it
            if ext.upper() == ".ZIP":
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as dl_executor:
                    future = dl_executor.submit(self.extract_file, path=path, into=root, final_into=final_root)
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
                src = os.path.join(r['into'], f) #"%s/%s" % (r['into'], f)
                src_name = os.path.split(src)[1] # get file name
                dst = os.path.join(r['final_into'], src_name) #"%s/%s" % (r['final_into'], src_name)
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
        everything) are moved into final_into (this is done in the callback)."""
        
        print "EXTRACTING PATH:", path
        with zipfile.ZipFile(path, 'r') as z:
            # Extract all to d.root...
            z.extractall(into)
            # Then check to see if the files extracted contained more zip files!
            #drc = ''

            extracted_files = []
            dirs = []
            #print z.namelist()
            # For each extracted file
            for name in z.namelist():
                # Move file into root directory
                drc, fname = os.path.split(name)
                __, ext = os.path.splitext(fname)
                #print fname, ext.upper()
                if ext.upper() == ".ZIP":
                    res = self.extract_file(os.path.join(into, name), into) #"%s/%s" % (into, name), into)
                    extracted_files.extend(res['files'])
                    dirs.extend(res['dirs'])
                else:
                    extracted_files.extend([name])
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
