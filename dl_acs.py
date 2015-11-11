import os
import click
import shutil
import logging
import pprint
from colorama import Fore, Back, Style
from functools import partial

from AcsServer import AcsServer
from Local import Local
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
    click.echo("Downloading SF")
    #logger = logging.getLogger()
    #click.echo(ctx.years)


    years = range(startyear, endyear+1)
    durations = [int(dur) for dur in durs]


    logger.debug("Years: {0}".format(years))
    logger.debug("Durations: {0}".format(durations))

    acs = AcsServer(baseurl=baseurl, years=years, durs=durations, pums=False)
    local = Local(os.path.normpath(outdir), overwrite=overwrite, pums=False)

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
def pums(states, baseurl, startyear, endyear, durs, overwrite, outdir, dryrun):
    """Download Summary File datafiles"""
    click.echo("Downloading PUMS")

    years = range(startyear, endyear+1)
    durations = [int(dur) for dur in durs]

    logger.debug("Years: {0}".format(years))
    logger.debug("Durations: {0}".format(durations))

    acs = AcsServer(baseurl=baseurl, years=years, durs=durations, pums=True)
    local = Local(os.path.normpath(outdir), overwrite=overwrite, pums=True)

    click.echo(pprint.pformat(acs.rooturls))

    for year in years:
        for dur in durations:
            # Check for invalid combinations
            if (year <= 2006 and dur != 1) or (year <= 2008 and dur == 5) or (year > 2013 and dur == 3):
                logger.info("Skipping invalid year/duration combination: {0} {1}-year".format(year, dur))
                continue

            new_states = [s for s in states if overwrite or not
                            os.path.exists(local.destination_paths(year, dur, s)['zip_path'])]
            
            if len(new_states) == 0:
                logger.info("Skipping {year} {dur}-year: All states already downloaded ({states})".format(year=year, dur=dur, states=states))

            #logger.info(Fore.GREEN + Style.BRIGHT + "{0} {1}-year: {2}".format(year, dur, new_states) + Fore.RESET + Style.RESET_ALL)
            #logger.debug("New States: {0}".format(new_states))
            click.secho("{0} {1}-year: {2}".format(year, dur, new_states), fg='green')

            state_data_files = acs.state_data_files(year, dur, new_states)
            #logger.debug("Data files to download: \n{0}{1}{2}".format(Fore.MAGENTA, pprint.pformat([str(f['url']).replace(acs.urlroot, "") for f in state_data_files]), Fore.RESET))
            #click.secho("Data files to download: \n{0}".format(pprint.pformat([str(f['url']).replace(acs.urlroot, "") for f in state_data_files])), fg='magenta')

            #stubs_and_doc_files = acs.stubs_and_documentation(year, dur)

            #logger.debug("Documentation files to download: \n{0}{1}{2}".format(Fore.GREEN, pprint.pformat(stubs_and_doc_files), Fore.RESET))
            #remote_files = acs.files_to_download(year, dur, new_states)
            #logger.debug(pprint.pformat(remote_files))
            #logger.debug("Files to download: \n{0}{1}{2}".format(Fore.MAGENTA, pprint.pformat([str(f['url'] + f['file']).replace(acs.urlroot, "") for f in [filesets for filesets in remote_files]]), Fore.RESET))

            if not dryrun:
                local.download_data_files(state_data_files, year, dur)
                #local.download_stubs_and_docs(stubs_and_doc_files, year, dur)