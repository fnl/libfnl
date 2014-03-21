#!/usr/bin/env python3

"""corpus parses and stores corpora in a Couch DB"""

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from functools import partial
from fnl.couch.broker import Server, COUCHDB_URL
import logging
from multiprocessing import Pool
import os
import sys

__author__ = 'Florian Leitner'
__version__ = '0.1'

DEFAULT_CORPUS='genia'
DEFAULT_ENCODING=sys.getdefaultencoding()
ANNOTATORS = {
    'genia': 'http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA'
}

def read(encoding, update, reader, annotator, couchdb_url, db_name, file_name):
    #noinspection PyBroadException
    try:
        couch = Server(couchdb_url)
        db = couch[db_name]

        with open(file_name, encoding=encoding) as stream:
            basename = os.path.basename(file_name)
            logging.info("parsing %s", basename)

            for article_id, article in reader.toText(stream):
                json = article.toJson()
                json['tags'] = article.tagsAsDict()
                json['annotator'] = annotator
                json['_id'] = article_id

                if update and article_id in db:
                    json['_rev'] = db.rev(article_id)

                db.save(json)

            logging.info("completed %s", basename)
    except:
        logging.exception("reading %s failed", file_name)

def main(corpus_files, update:bool=False, corpus:str=DEFAULT_CORPUS,
         encoding:str=DEFAULT_ENCODING, couchdb_url:str=COUCHDB_URL,
         database:str=DEFAULT_CORPUS):
    """
    :param corpus_files: A list of file names to parse.
    :param update:
    :param corpus: The name of the corpus type to parse.
    :param encoding: The encoding used by the corpus files.
    """
    try:
        fnl = __import__("fnl.nlp.{}.corpus".format(corpus), globals())
        C = getattr(fnl.nlp, corpus).corpus
    except ImportError:
        raise ValueError("no corpus reader for {}".format(corpus))

    pool = Pool()
    read_file = partial(read, encoding, update, C.CorpusReader(),
                        ANNOTATORS[corpus], couchdb_url, database)
    pool.map(read_file, corpus_files)
    pool.close()
    pool.join()
    return 0

if __name__ == '__main__':
    from optparse import OptionParser

    usage = "%prog [options] <corpus-type> <infile>..."
    epilog = "system (default) locale: LANG=%s" % os.getenv("LANG")

    parser = OptionParser(
        usage=usage, version=__version__, description=__doc__,
        prog=os.path.basename(sys.argv[0]), epilog=epilog
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.set_defaults(corpus=DEFAULT_CORPUS)

    parser.add_option(
        "-e", "--encoding", default=DEFAULT_ENCODING, metavar="E",
        help="text encoding of corpus [%default]"
    )
    parser.add_option(
        "-u", "--update", action="store_true", default=False,
        help="update files already in the database"
    )
    parser.add_option(
        "--genia", action="store_const", const='genia',
        dest="corpus", help="parse GENIA XML corpus type [default]"
    )
    parser.add_option(
        "--couchdb-url", default=COUCHDB_URL,
        help="$COUCHDB_URL [%default]"
    )
    parser.add_option(
        "--database", default=DEFAULT_CORPUS,
        help="Couch database name [%default]"
    )
    parser.add_option(
        "--error", action="store_const", const=logging.ERROR,
        dest="loglevel", help="error log level only [warn]"
    )
    parser.add_option(
        "--info", action="store_const", const=logging.INFO,
        dest="loglevel", help="info log level [warn]"
    )
    parser.add_option(
        "--debug", action="store_const", const=logging.DEBUG,
        dest="loglevel", help="debug log level [warn]"
    )
    parser.add_option("--logfile", help="log to file, not STDERR")

    opts, args = parser.parse_args()
    if len(args) < 1: parser.error("no input file")
    if not opts.corpus: parser.error("no corpus type selected")

    logging.basicConfig(
        filename=opts.logfile, level=opts.loglevel,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    kwds = opts.__dict__
    del kwds["logfile"]
    del kwds["loglevel"]
    sys.exit(main(args, **kwds))
