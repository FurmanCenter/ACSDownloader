import click


class CensusDownloader(object):
	def __init__(self):
		"""Class to hold downloader context."""
		pass

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