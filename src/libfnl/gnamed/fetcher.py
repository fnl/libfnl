"""
.. py:module:: libfnl.gnamed.fetcher
   :synopsis: Functions to download repository files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import os
import re
import sys

from urllib.request import urlopen, urlretrieve

from libfnl.gnamed.constants import REPOSITORIES

def Retrieve(*repo_keys:str, directory:str=os.getcwd(),
             encoding:str=sys.getdefaultencoding()):
    """
    :param repo_keys: keys of the repositories to download
    :param directory: target directory to store the downloaded files
    :param encoding: encoding to use for text files
    """
    for db in repo_keys:
        logging.info('downloading files for "%s"', db)
        repo = REPOSITORIES[db]
        url = repo['url']

        for path, filename, remote_enc in repo['resources']:
            logging.debug("connecting to '%s%s'", url, path)
            logging.info("streaming into '%s' (%s)",
                         os.path.join(directory, filename), encoding)

            if remote_enc is not None:
                stream = urlopen(url + path)
                info = stream.info()

                if 'content-type' in info and\
                   'charset' in info['content-type']:
                    mo = re.search('charset\s*=\s*(.*?)\s*$',
                                   info['content-type'])

                    if remote_enc != mo.group(1):
                        remote_enc = mo.group(1)
                        logging.warn("remote encoding at %s is %s",
                                     url + path, remote_enc)

                output = open(os.path.join(directory, filename), mode='w',
                              encoding=encoding)

                for data in stream:
                    output.write(data.decode(remote_enc))

                output.close()
                stream.close()
            else:
                urlretrieve(url + path, os.path.join(directory, filename))

            print(os.path.join(directory, filename), file=sys.stdout)
