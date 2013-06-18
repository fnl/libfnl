#!/usr/bin/env python3
"""maintain a MEDLINE/PubMed repository"""
import logging
import os
import sys

from sqlalchemy.exc import OperationalError


__author__ = 'Florian Leitner'
__version__ = '1'


def Main(command, files_or_pmids, session):
    """
    :param command: one of create/read/update/delete
    :param files_or_pmids: the list of files or PMIDs to process
    """
    from libfnl.medline.crud import create, read, update, delete

    if command == 'create':
        return create(session, files_or_pmids)
    elif command == 'read':
        return read(session, [int(i) for i in files_or_pmids])
    elif command == 'update':
        return update(session, files_or_pmids)
    elif command == 'delete':
        return delete(session, [int(i) for i in files_or_pmids])


def WriteRecords(query, tiab:bool, output_dir:str):
    for rec in query:
        logging.debug("writing%s PMID %i", " TIAB from" if tiab else "", rec.pmid)
        file = open(os.path.join(output_dir, "{}.txt".format(rec.pmid)), 'wt')
        WriteSection(file, rec, 'Title')

        if not tiab:
            WriteSection(file, rec, 'Vernacular')

            for author in rec.authors:
                print(author.fullName(), file=file)

            print('', file=file)

        for sec in ('Abstract', 'Background', 'Objective', 'Methods', 'Results',
                    'Conclusions', 'Unlabelled'):
            WriteSection(file, rec, sec)

        if not tiab:
            WriteSection(file, rec, 'Copyright')
            for desc in rec.descriptors:
                print('+' if desc.major else '-', desc.name, file=file)
                for qual in desc.qualifiers:
                    print('+' if qual.major else '-', qual.name, file=file)
                print('', file=file)
            for ns, i in rec.identifiers.items():
                print('{}:{}'.format(ns, i.value), file=file)


def WriteSection(file, rec, sec):
    if sec in rec.sections:
        s = rec.sections[sec]
        if (s.label is not None):
            print(s.label, file=file)
        print(s.content, end='\n\n', file=file)


if __name__ == '__main__':
    from argparse import ArgumentParser
    from libfnl.medline.orm import initdb, Session

    epilog = 'system (default) encoding: {}'.format(sys.getdefaultencoding())

    parser = ArgumentParser(
        usage='%(prog)s [options] URL CMD FILE/PMID ...',
        description=__doc__, epilog=epilog,
        prog=os.path.basename(sys.argv[0])
    )

    parser.set_defaults(loglevel=logging.WARNING)

    parser.add_argument(
        'url', metavar='URL', help='a database URL string'
    )
    parser.add_argument(
        'command', metavar='CMD', help='command: [dump|create|write|update|delete]'
    )
    parser.add_argument(
        'files', metavar='FILE/PMID', nargs='+', help='MEDLINE XML files or PMIDs'
    )
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--tiab', action='store_true', help='write only title/abstract')
    parser.add_argument(
        '--output', metavar='DIR', default=os.path.curdir,
        help='dump/write to a specific directory'
    )
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

    if args.command not in ('dump', 'create', 'write', 'update', 'delete'):
        parser.error('illegal command "{}"'.format(args.command))

    if (args.command == 'dump'):
        from libfnl.medline.crud import dump
        result = dump(args.files, args.output)
    else:
        try:
            initdb(args.url)
        except OperationalError as e:
            parser.error(str(e))

        result = Main(args.command, args.files, Session())

        if args.command == 'read':
            WriteRecords(result, args.tiab, args.output)
            result = True

    sys.exit(0 if result else 1)
