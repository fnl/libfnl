#!/usr/bin/env python3

"""Count the number of times a gene/protein appears in MEDLINE."""

import logging
import os
import sys

from libfnl.medline.orm import InitDb as InitMedline
from libfnl.gnamed.orm import InitDb as InitGnamed

__author__ = 'Florian Leitner'
__version__ = '1'


def main(proteins:bool):
    """
    :param proteins: count protein symbols instead of gene symbols
    """
    from libfnl.stat.gpcount import CountGenes, CountProteins

    if proteins:
        CountProteins()
    else:
        CountGenes()


if __name__ == '__main__':
    from argparse import ArgumentParser

    epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())

    parser = ArgumentParser(
        usage='%(prog)s [options] FILE ...',
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)

    parser.add_argument(
        'medline', metavar='MEDLINE_URL', type=str, help='MEDLINE DB URL'
    )
    parser.add_argument(
        'gnamed', metavar='GNAMED_URL', type=str, help='gnamed DB URL'
    )
    parser.add_argument(
        '-p', '--proteins', action='store_true', help='count protein symbols'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '--error', action='store_const', const=logging.ERROR,
        dest='loglevel', help='error log level only [warn]'
    )
    parser.add_argument(
        '--info', action='store_const', const=logging.INFO,
        dest='loglevel', help='info log level [warn]'
    )
    parser.add_argument(
        '--debug', action='store_const', const=logging.DEBUG,
        dest='loglevel', help='debug log level [warn]'
    )
    parser.add_argument('--logfile', metavar='FILE', help='log to file, not STDERR')

    args = parser.parse_args()
    logging.basicConfig(
        filename=args.logfile, level=args.loglevel,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s'
    )

    InitMedline(args.medline)
    InitGnamed(args.gnamed)

    sys.exit(main(args.proteins))
