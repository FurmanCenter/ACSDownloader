import os
import click


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