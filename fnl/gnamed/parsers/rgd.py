"""
.. py:module:: libfnl.gnamed.parsers.rgd
   :synopsis: A RGD (Rat Genome Database) GENES file parser.

`ftp://rgd.mcw.edu/pub/data_release/GENES_README`_

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import io
import logging

from collections import namedtuple
from sqlalchemy.orm.exc import NoResultFound

from libfnl.gnamed.constants import Species, Namespace
from libfnl.gnamed.loader import GeneRecord, AbstractLoader, DBRef, DuplicateEntityError
from libfnl.gnamed.orm import GeneRef, Gene

CONTENT = [
    (0, 'id'),
    (1, 'symbol'),
    (2, 'name'),
    (3, 'descriptions'),
    (5, 'chromosome'),
    (7, 'location'),
    (20, Namespace.entrez),
    (21, Namespace.uniprot),
    (29, 'old_symbols'),
    (30, 'old_names'),
    (32, 'qtl_symbols'),
]

COLUMNS = list(zip(*CONTENT))[0]
FIELDS = list(zip(*CONTENT))[1]

Line = namedtuple('Line', FIELDS)

class Parser(AbstractLoader):
    """
    A parser for RGD (rgd.mcw.edu) records.

    Implements the `AbstractParser._parse` method.

    Note that GENES_HUMAN and _MOUSE cannot be incorporated because RGD does
    not map these genes to unique instances (i.e., a RGD human or mouse "gene"
    can map to multiple genes).
    """

    def _setup(self, stream:io.TextIOWrapper):
        lines = super(Parser, self)._setup(stream)
        content = stream.readline().strip()
        lines += 1

        while content.startswith('#'):
            content = stream.readline().strip()
            lines += 1

        logging.debug("file header:\n%s", content)
        return lines

    def _parse(self, line:str):
        items = [i.strip() for i in line.split('\t')]
        assert len(items) > 32, '{} items'.format(len(items))

        for idx in COLUMNS:
            if not items[idx] or items[idx] == '-':
                items[idx] = None

        row = Line._make(items[col] for col in COLUMNS)
        #noinspection PyTypeChecker
        record = GeneRecord(Species.rat, symbol=row.symbol, name=row.name,
                            chromosome=row.chromosome,
                            location=(
                                '{}{}'.format(row.chromosome, row.location)
                                if row.chromosome and row.location else None
                            ))
        db_key = DBRef(Namespace.rgd, row.id)

        # add DB references
        record.addDBRef(db_key)

        for ns in (Namespace.entrez, Namespace.uniprot):
            accs = getattr(row, ns)

            if accs:
                if ns == Namespace.uniprot:
                    # noinspection PyUnresolvedReferences
                    for acc in accs.split(';'):
                        record.addDBRef(DBRef(ns, acc))
                else:
                    # noinspection PyUnresolvedReferences
                    accs = accs.split(';')
                    record.addDBRef(DBRef(ns, accs[0]))

        # parse symbol strings
        if row.symbol:
            record.addSymbol(row.symbol)

        for field in (row.old_symbols, row.qtl_symbols):
            if field:
                for symbol in field.split(';'):
                    record.addSymbol(symbol)

        # parse name strings
        if row.name:
            record.addName(row.name)

        if row.old_names:
            for name in row.old_names.split(';'):
                record.addName(name.strip())

        # parse keywords strings
        if row.descriptions:
            for desc in row.descriptions.split('; '):
                record.addKeyword(desc.strip())

        try:
            self._loadRecord(db_key, record)
        except DuplicateEntityError:
            accs = getattr(row, Namespace.entrez)

            if accs:
                # Entrez Gene is not unique, having created multiple GIs for the same gene.
                # Sometimes, single Entrez Genes are badly linked by RGD, as in the case of
                # RGD:69363 linking to GI:113900, that should be linked to GI:10092108. This code
                # can update such artifacts in RGD, too, and eliminates the duplicate Genes.
                logging.warning('removing duplicate rat genes for rgd:%s with Entrez GIs %s',
                                row.id, accs)
                rgd_ref = self.session.query(GeneRef).filter(
                    GeneRef.accession == row.id
                ).filter(GeneRef.namespace == Namespace.rgd).one()
                logging.debug('correct %s links to gene:%s', repr(rgd_ref), rgd_ref.id)
                orphan_genes = {}

                # Update retired RGD and Entrez entries by pointing the outdated
                # Refs to the right Gene (rgd_ref.id), while deleting the "duplicate" Genes.
                # noinspection PyUnresolvedReferences
                for gi in accs.split(';'):
                    entrez_ref = self.session.query(GeneRef).filter(
                        GeneRef.accession == gi
                    ).filter(GeneRef.namespace == Namespace.entrez).one()

                    if entrez_ref.id != rgd_ref.id:
                        try:
                            retired_ref = self.session.query(GeneRef).filter(
                                GeneRef.id == entrez_ref.id
                            ).filter(GeneRef.namespace == Namespace.rgd).one()
                            logging.debug('updating %s and retired %s reference to orphan gene:%s',
                                          repr(entrez_ref), repr(retired_ref), entrez_ref.id)
                            retired_ref.id = rgd_ref.id
                        except NoResultFound:
                            logging.debug('updating %s reference to orphan gene:%s',
                                          repr(entrez_ref), entrez_ref.id)

                        if entrez_ref.id not in orphan_genes:
                            orphan_genes[entrez_ref.id] = self.session.query(Gene).filter(
                                Gene.id == entrez_ref.id
                            ).one()

                        entrez_ref.id = rgd_ref.id

                for gene in orphan_genes.values():
                    self.session.delete(gene)

                self._flush()
                self._loadRecord(db_key, record)
            else:
                raise

        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        records = super(Parser, self)._cleanup(file)
        return records
