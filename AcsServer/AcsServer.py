import logging
import pprint
import re
from utils import valid_url, get_links, state_filestub
logger = logging.getLogger(__name__)

class AcsServer(object):
    '''An object representing the ACS server environment.'''

    def __init__(self, years, durs=[1, 3, 5], rooturls = None, baseurl=None, pums=False):
        """ statesurl is a dict of durations """
        self.pums = pums
        self.durs = list(durs)
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