#!/usr/bin/env python3

"""Parse and store a corpus to its Couch DB."""

from functools import partial
from libfnl.couch.broker import Server
import logging
from multiprocessing import Pool
import os
import sys

__author__ = "Florian Leitner"
__version__ = "0.1"

DEFAULT_CORPUS="genia"
DEFAULT_ENCODING=os.getenv("LANG", "en_US.UTF-8").split(".")[1]

def read(encoding, update, reader, corpus, file_name):
    #noinspection PyBroadException
    try:
        couch = Server()
        db = couch[corpus]

        with open(file_name, encoding=encoding) as stream:
            basename = os.path.basename(file_name)
            logging.info("parsing %s", basename)

            for article in reader.toText(stream):
                binary = article.toBinary("utf-8")
                binary.metadata["source"] = basename
                result = binary.save(db, update=update)
                assert result, \
                    logging.error("saving article from %s failed", basename)

            logging.info("completed %s", basename)
    except Exception:
        logging.exception("reading %s failed", file_name)

def main(corpus_files, update:bool=False, corpus:str=DEFAULT_CORPUS,
         encoding:str=DEFAULT_ENCODING):
    """
    :param corpus_files: A list of file names to parse.
    :param corpus: The name of the corpus type to parse.
    :param encoding: The encoding used by the corpus files.
    """
    try:
        libfnl = __import__("libfnl.nlp.{}.corpus".format(corpus), globals())
        C = getattr(libfnl.nlp, corpus).corpus
    except ImportError:
        raise ValueError("no corpus reader for {}".format(corpus))

    pool = Pool()
    read_file = partial(read, encoding, update, C.CorpusReader(), corpus)
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
    parser.set_defaults(corpus=None)

    parser.add_option(
        "-e", "--encoding", default=DEFAULT_ENCODING, metavar="E",
        help="text encoding of corpus [%default]"
    )
    parser.add_option(
        "-u", "--update", action="store_true", default=False,
        help="only update files on the database"
    )
    parser.add_option(
        "--genia", action="store_const", const="genia",
        dest="corpus", help="GENIA XML corpus type, stored in DB 'genia'"
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
