import os
import logging
import zipfile
import concurrent.futures
import shutil
from local_utils import safe_make_dir, download

logger = logging.getLogger(__name__)



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
        yd_path = os.path.normpath(
                    "{0}{3}ACS{1}_{2}yr".format(self.outdir, year, dur, os.path.sep))

        safe_make_dir(yd_path)

        print "YEAR/DUR destination {}: {}".format(self.pums, yd_path)
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