
import requests
from bs4 import BeautifulSoup as bs
import us


def valid_url(url):
    '''Test if URL is valid (successful return code)'''
    r = requests.get(url)
    return (r.status_code == requests.codes.ok)

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

    >>> get_links('http://www2.census.gov/acs2005/summaryfile/',
    ... link_filter=lambda h: h if not h.find('/') >= 0 else None)
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


def state_filestub(st, is2005=False):
    """Given a 2-char abbreviation, return the state filestub (directory).

    The Census standard is the full state name, camel case, spaces
    removed. This generally is true for "United States" too, but in 2005
    they put a "0" in front of the name, to make sure it's sorted to the top.

    >>> print state_filestub("NY")
    NewYork
    
    >>> print state_filestub("US")
    UnitedStates

    >>> print state_filestub("us", is2005=True)
    0UnitedStates
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

    >>> print acs_year_dur_filter('/acs2005/')
    {'dur': 1, 'href': '/acs2005', 'dir': 'acs2005', 'year': 2005}

    >>> print acs_year_dur_filter('http://www2.census.gov/acs2009_5yr/')
    {'dur': 5, 'href': 'http://www2.census.gov/acs2009_5yr', 'dir': 'acs2009_5yr', 'year': 2009}

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
