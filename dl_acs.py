import os
import requests
from bs4 import BeautifulSoup as bs
import click


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
	['ACS_2005_SF_Tech_Doc.pdf', 'ACS_SF_Worked_Example.pdf', 'README.pdf']

	"""
    r = requests.get(url)
    soup = bs(r.text)
    links = soup.select('td a') # get all links in a table cell

    if filter is not None:
    	return [filter(link['href']) for link in links]
    else:
    	return [link['href'] for link in links]


class CensusDownloader(object):
	"""Class to hold downloader context.

	"""
	
	def __init__(self, outdir,
				baseurl, maxyear,
				years, durations, states):
		"""Init method"""

		self.outdir = outdir

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
	def remote_files(self):
	    return self._remote_files

	@property
	def dest_files(self):
	    return self._dest_files
	
	

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