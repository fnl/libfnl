#!/usr/bin/env python3

"""Calculate inter-rater agreements from subject-vote TSV's per rater."""

import logging
import os
import sys
from types import FunctionType
from libfnl.stat.kappa import Fleiss, CreateRatingMatrix

__author__ = "Florian Leitner"
__version__ = "1.0"

def main(*file_names:tuple([str]), subject_col:int=1, rating_col:int=2, Kappa:FunctionType=Fleiss):
    """
    :param file_names: File names of subject-vote TSV's; one per rater.
    :param subject_col: Subjects are read from the given column.
    :param rating_col: Ratings (votes) are expected to be in the given column.
    :param Kappa: The :py:module:`libfnl.stat.kappa` function to use.
    """
    ratings = []

    for fn in file_names:
        ratings.append({sub: vote for sub, vote in TsvReader(fn, subject_col, rating_col)})

    logging.debug("Ratings: %s", ratings)
    M = CreateRatingMatrix(ratings)
    print(Kappa(M))
    return 0


def TsvReader(files:str, subject_col:int, rating_col:int):
    """
    Yield ``(str, str)`` tuples from a list of *files* in TSV format.

    The first string is from the *subject_col* column, the second from the
    column number as indicated by *rating_col*.
    """
    rc = rating_col - 1
    sc = subject_col - 1
    for lno, line in enumerate(open(files)):
        if ord(line[0]) == 0xFEFF: line = line[1:]
        if line.strip()[0] == "#": continue
        items = line.split('\t')

        try:
            logging.debug("vote for %s: %s", items[sc], items[rc])
            yield items[sc].strip(), items[rc].strip()
        except IndexError:
            raise ValueError(
                "line {} in {} malformed".format(lno + 1, files)
            )

if __name__ == '__main__':
    from optparse import OptionParser

    usage = "%prog [options] <infile>..."
    epilog = "Note: Subject IDs must always be in the first column. " \
        "If a lines starts with '#', it is ignored (ie. a comment)."

    parser = OptionParser(
        usage=usage, version=__version__, description=__doc__,
        prog=os.path.basename(sys.argv[0]), epilog=epilog
    )

    parser.set_defaults(loglevel=logging.WARNING)
    parser.set_defaults(Kappa=Fleiss)

    parser.add_option(
        "--fleiss", action="store_const", const=Fleiss,
        dest="Kappa", help="use Fleiss' Kappa [default]"
    )
    parser.add_option(
        "-s", "--subject-col", action="store", type="int", default=1,
        metavar="COL", help="read subjects from that column [1st]"
    )
    parser.add_option(
        "-r", "--rating-col", action="store", type="int", default=2,
        metavar="COL", help="read ratings from that column [2nd]"
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
    if len(args) < 2: parser.error("at least two rating files required")

    logging.basicConfig(
        filename=opts.logfile, level=opts.loglevel,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    kwds = opts.__dict__
    del kwds["logfile"]
    del kwds["loglevel"]
    sys.exit(main(*args, **kwds))

