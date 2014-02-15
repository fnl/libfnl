"""
.. py:module:: libfnl.gnamed.parsers.tair
   :synopsis: A TAIR gene names (primary gene symbol) and aliases file parser.

`ftp://ftp.arabidopsis.org/home/tair/Genes/`_

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import io
from libfnl.gnamed.constants import Namespace, Species
from libfnl.gnamed.loader import AbstractLoader, DuplicateEntityError, DBRef, GeneRecord


class Parser(AbstractLoader):
    """
    A parser for TAIR primary gene symbol, alias and entrez mapping lists.

    Implements the `AbstractParser._parse` method.

    Note that GENES_HUMAN and _MOUSE cannot be incorporated because RGD does
    not map these genes to unique instances (i.e., a RGD human or mouse "gene"
    can map to multiple genes).
    """

    def _setup(self, stream:io.TextIOWrapper):
        assert len(self.files) == 3, \
            'received {} files, expected 3'.format(len(self.files))
        lines = super(Parser, self)._setup(stream)

        if not hasattr(self, '_records'):
            self._records = dict()

        if not hasattr(self, '_fileno'):
            self._fileno = 0

        if stream.name.endswith('names.txt'):
            content = stream.readline().strip()
            lines += 1
            logging.debug("file header:\n%s", content)
            self._parse = self._parseName
            self._fileno += 1
        elif stream.name.endswith('aliases.txt'):
            logging.debug('parsing aliases')
            content = stream.readline().strip()
            lines += 1
            logging.debug("file header:\n%s", content)
            self._parse = self._parseAlias
            self._fileno += 1
        elif stream.name.endswith('tair.txt'):
            logging.debug('parsing EntrezGene links')
            self._parse = self._parseEntrez
            self._fileno += 1
        else:
            raise RuntimeError('unknown TAIR file "{}"'.format(stream.name))

        return lines

    def _parseName(self, line:str):
        items = [i.strip() for i in line.split('\t')]
        if len(items) == 2:
            # noinspection PyTypeChecker,PyTypeChecker
            items.append(None)
        elif len(items[2]) > 0 and items[2][0] == '"' and items[2][-1] == '"':
            items[2] = items[2][1:-1]
        assert len(items) == 3, '{} items'.format(len(items))
        db_key = DBRef(Namespace.tair, items[0])
        #noinspection PyTypeChecker
        record = GeneRecord(Species.cress, symbol=items[1], name=items[2],
                            #chromosome=?, location=?
                            )
        record.addDBRef(db_key)
        record.addSymbol(items[1])
        if items[2] is not None:
            record.addName(items[2])
        self._records[db_key] = record
        logging.debug('parsed the name for %s:%s', *db_key)
        return 1

    def _parseAlias(self, line:str):
        items = [i.strip() for i in line.split('\t')]
        if len(items) == 2:
            # noinspection PyTypeChecker,PyTypeChecker
            items.append(None)
        elif len(items[2]) > 0 and items[2][0] == '"' and items[2][-1] == '"':
            items[2] = items[2][1:-1]
        assert len(items) == 3, '{} items'.format(len(items))
        if len(items) == 2:
            # noinspection PyTypeChecker
            items.append(None)
        db_key = DBRef(Namespace.tair, items[0])

        if db_key not in self._records:
            logging.warning("unknown record {}".format(items))
            return 0
        else:
            record = self._records[db_key]
            record.addSymbol(items[1])
            if items[2] is not None:
                record.addName(items[2])
            logging.debug('parsed an alias for %s:%s', *db_key)
            return 1

    def _parseEntrez(self, line:str):
        gene_id, tair_id = line.split('\t')
        db_key = DBRef(Namespace.tair, tair_id.strip())
        ref = DBRef(Namespace.entrez, gene_id.strip())
        if db_key not in self._records:
            logging.info(
                "unknown record %s:%s links to %s:%s",
                db_key.namespace, db_key.accession,
                ref.namespace, ref.accession
            )
            return 0
        else:
            self._records[db_key].addDBRef(ref)
            logging.debug('parsed a link to %s:%s', *ref)
            return 1

    def _cleanup(self, file:io.TextIOWrapper):
        num_records = super(Parser, self)._cleanup(file)

        if self._fileno == 3:
            logging.info('loading %s parsed records', len(self._records))

            for db_key, record in self._records.items():
                try:
                    self._loadRecord(db_key, record)
                except DuplicateEntityError:
                    if len(record.refs) == 2:
                        # assume all TAIR links that do not coincide with the
                        # Entrez back-links are bad, as it will be always
                        # TAIR that is not up-to-date.
                        logging.info('removing likely bad Entrez ref in %s:%s',
                                     *db_key)
                        assert any(r.namespace == Namespace.entrez
                                   for r in record.refs), record.refs
                        record.refs = {r for r in record.refs if
                                       r.namespace == Namespace.tair}
                        assert len(record.refs) == 1, record.refs
                        self._loadRecord(db_key, record)
                    else:
                        raise

        return num_records
