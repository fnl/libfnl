#!/usr/bin/env python3
"""bootstrap a gene/protein name/reference repository"""
import libfnl.gnamed
import logging
import sys
import os

from argparse import ArgumentParser
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError

from libfnl.gnamed.constants import REPOSITORIES
from libfnl.gnamed.fetcher import Retrieve
from libfnl.gnamed.orm import InitDb
from libfnl.gnamed.parsers import taxa

_cmd = None

for a in sys.argv:
    if a in ['fetch', 'load', 'init']:
        _cmd = a
        break

if _cmd == 'fetch':
    _usage = "%(prog)s [options] fetch KEY [KEY...]"
    _description = "download a repository"
elif _cmd == 'init':
    _usage = "%(prog)s [options] init FILE FILE FILE"
    _description = "initialize the DB"
elif _cmd == 'load':
    _usage = "%(prog)s [options] load KEY FILE [FILE...]"
    _description = "load a repository into the DB"
else:
    _usage = "%(prog)s [options] CMD [args...]"
    _description = __doc__

parser = ArgumentParser(
    usage=_usage, description=_description,
    prog=os.path.basename(sys.argv[0]),
    epilog="(c) Florian Leitner 2012. All rights reserverd. License: aGPL v3."
)

parser.set_defaults(loglevel=logging.WARNING)

parser.add_argument(
    'command', metavar='CMD', nargs='?',
    choices=['fetch', 'init', 'load'],
    help="one of: fetch, init, load (see --help CMD)"
)
parser.add_argument(
    '--version', action='store_true',
    help="print version and exit"
)
parser.add_argument(
    '--list', action='store_true',
    help="list available repository keys and exit"
)

if _cmd in ('init', 'load'):
    parser.add_argument(
        '--database', metavar='DB', action='store',
        default=os.getenv('PGDATABASE', "gnamed_tmp"),
        help="database name [PGDATABASE=%(default)s]"
    )
    parser.add_argument(
        '--host', action='store',
        default=os.getenv('PGHOST', "localhost"),
        help="database host [PGHOST=%(default)s]"
    )
    parser.add_argument(
        '--port', action='store', type=int,
        default=int(os.getenv('PGPORT', "5432")),
        help="database port [PGPORT=%(default)s]"
    )
    parser.add_argument(
        '--driver', action='store',
        default='postgresql+psycopg2',
        help="database driver [%(default)s]"
    )
    parser.add_argument(
        '-u', '--username', metavar='NAME', action='store',
        default=os.getenv('PGUSER'),
        help="database username [PGUSER=%(default)s]"
    )
    parser.add_argument(
        '-p', '--password', metavar='PASS', action='store',
        default=os.getenv('PGPASSWORD'),
        help="database password [PGPASSWORD=%(default)s]"
    )

if _cmd == 'fetch':
    parser.add_argument(
        'repositories', metavar='KEY [KEY ...]', nargs='*',
        help="keys of all repositories to fetch"
    )
    parser.add_argument(
        '-d', '--directory', metavar="DIR", action='store',
        default=os.getcwd(),
        help="store files to specified directory [CWD]"
    )
elif _cmd == 'init':
    parser.add_argument(
        'nodes', metavar='FILE', nargs='?',
        help="a nodes.dmp NCBI Taxonomy file"
    )
    parser.add_argument(
        'names', metavar='FILE', nargs='?',
        help="a names.dmp NCBI Taxonomy file"
    )
    parser.add_argument(
        'merged', metavar='FILE', nargs='?',
        help="a merged.dmp NCBI Taxonomy file"
    )
elif _cmd == 'load':
    parser.add_argument(
        'repository', metavar='KEY', nargs='?',
        help="repository key to load"
    )
    parser.add_argument(
        'files', metavar='FILE [FILE ...]', nargs='*',
        help="path to the file(s) to load"
    )

parser.add_argument(
    '-e', '--encoding', action='store', metavar="ENC",
    default=sys.getdefaultencoding(),
    help="process text files using specified encoding [%(default)s]"
)
parser.add_argument(
    '--error', action='store_const', const=logging.ERROR,
    dest='loglevel', help="set log level error [warn]"
)
parser.add_argument(
    '--info', action='store_const', const=logging.INFO,
    dest='loglevel', help="set log level info [warn]"
)
parser.add_argument(
    '--debug', action='store_const', const=logging.DEBUG,
    dest='loglevel', help="set log level debug [warn]"
)
parser.add_argument(
    '--logfile', metavar="FILE", help="log to file, not STDERR"
)

args = parser.parse_args()

logging.basicConfig(
    filename=args.logfile, level=args.loglevel,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s"
)

if args.loglevel <= logging.DEBUG:
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

if args.version:
    print(libfnl.gnamed.__version__)
elif args.list:
    for key in REPOSITORIES:
        print("{}\t({})".format(key, REPOSITORIES[key]['description']))
elif args.command == 'fetch':
    logging.info('fetching %s', ', '.join(args.repositories))

    for repo_key in args.repositories:
        if repo_key not in REPOSITORIES:
            parser.error('repository key "{}" unknown'.format(repo_key))

    Retrieve(*args.repositories, directory=args.directory,
             encoding=args.encoding)
elif args.command == 'load' and args.repository:
    for file in args.files:
        if not os.path.exists(file):
            parser.error('file "{}" does not exist'.format(file))

    if not args.files:
        parser.error('no input files')

    if args.repository not in REPOSITORIES and args.repository[-2:] != 'pg':
        parser.error('repository key "{}" unknown'.format(args.repository))

    db_url = URL(args.driver, username=args.username, password=args.password,
                 host=args.host, port=args.port, database=args.database)
    logging.info('connecting to %s', db_url)

    try:
        InitDb(db_url)
    except OperationalError as oe:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.exception("DB error")
        parser.error(str(oe.orig).strip())

    if args.repository in ('entrezpg', 'uniprotpg'):
        repo_parser_module = __import__(
            'libgnamed.parsers.' + args.repository[:-2], globals(),
            fromlist=['SpeedLoader']
        )
        repo_parser = repo_parser_module.SpeedLoader(
            *args.files, encoding=args.encoding
        )
        userpass = "user={} password={} ".format(
            args.username, args.password
        ) if (args.username and args.password) else ""
        repo_parser.setDSN("{}host={} port={} dbname={}".format(
            userpass, args.host, args.port, args.database
        ))
    else:
        repo_parser_module = __import__(
            'libgnamed.parsers.' + args.repository, globals(),
            fromlist=['Parser']
        )
        repo_parser = repo_parser_module.Parser(*args.files,
                                                encoding=args.encoding)

    repo_parser.parse()
elif args.command == 'init':
    for file in (args.nodes, args.names, args.merged):
        if not file:
            parser.error('missing input files')
        if not os.path.exists(file):
            parser.error('file "{}" does not exist'.format(file))

    db_url = URL(args.driver, username=args.username, password=args.password,
                 host=args.host, port=args.port, database=args.database)
    logging.info('connecting to %s', db_url)

    try:
        InitDb(db_url)
    except OperationalError as oe:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.exception("DB error")
        parser.error(str(oe.orig).strip())

    taxa_parser = taxa.Parser(args.nodes, args.names, args.merged,
                              encoding=args.encoding)
    taxa_parser.parse()
else:
    parser.error('wrong number of arguments')
