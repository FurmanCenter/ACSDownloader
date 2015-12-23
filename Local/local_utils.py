import os
import requests
import logging
import click

def safe_make_dir(newdir):
    '''Try making new directory, do not throw error if already exists'''
    try:
        os.makedirs(newdir)
    except OSError as e:
        # If can't create directory because it already exists, then fine.
        # But if it doesn't already exist, there's some other
        # problem and we should raise the exception
        if not os.path.isdir(newdir):
            raise e

def download(url, path, chunk_size=1024*1024):
    """Download a file from a url to a file path

    Keyword arguments:
    url -- the URL of the file to be downloaded
    path -- the file path to serve as destination for downloaded file
    chunk_size -- the size of the file chunks (defaults to 1024^2)

    Returns a dictionary with following keys:
    'success' -- Boolean for whether downloaded without error
    'status' -- the status code
    'url' -- the URL downloaded from
    'path' -- the path of the downloaded file
    """
    r = requests.get(url, stream=True)
    if r.status_code != requests.codes.ok:
        logging.error("Got status %s from %s" % (r.status_code, url))
        return {'success': False, 'status': r.status_code, 'url': url, 'path': path}

    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        print "Downloading {0}".format(os.path.split(r.url)[1])
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                f.flush()
        # with click.progressbar(r.iter_content(chunk_size=chunk_size), label="Downloading {0}".format(os.path.split(r.url)[1])) as bar:
        #     for chunk in bar:
        #         if chunk:
        #             f.write(chunk)
        #             f.flush()

    return {'success': True, 'status': r.status_code, 'url': url, 'path': path}