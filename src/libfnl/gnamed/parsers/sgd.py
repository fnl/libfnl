"""
.. py:module:: libfnl.gnamed.parsers.sgd
   :synopsis: A SGD (Yeast Genome Database) names parser.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import io

from collections import namedtuple

from libfnl.gnamed.constants import Species, Namespace
from libfnl.gnamed.loader import GeneRecord, AbstractLoader, DBRef

CONTENT = [
    (0, 'id'),
    (1, 'qualifier'),
    (2, 'symbol'),
    (3, 'name'),
    (4, 'location'),
    (5, 'length'),
    (6, 'protein_name'),
    (7, 'alias'),
]

COLUMNS = list(zip(*CONTENT))[0]
FIELDS = list(zip(*CONTENT))[1]

Line = namedtuple('Line', FIELDS)

class Parser(AbstractLoader):
    """
    A simple parser for SGD (yeastmine.yeastgenome.org) gene name data.
    """

    def _setup(self, stream:io.TextIOWrapper):
        lines = super(Parser, self)._setup(stream)
        self._db_key = None
        self._record = None
        return lines

    def _parse(self, line:str):
        count = 0
        items = [i.strip() for i in line.split('\t')]
        assert len(items) == len(CONTENT), '{} items'.format(len(items))

        for i in range(len(items)):
            if items[i] == '""':
                items[i] = None

        row = Line._make(items)

        if self._db_key is None or row.id != self._db_key.accession:
            if self._record is not None:
                self._loadRecord(self._db_key, self._record)
                count = 1

            #noinspection PyTypeChecker
            record = GeneRecord(Species.budding_yeast,
                                symbol=row.symbol if row.symbol else row.location,
                                name=row.name,
                                chromosome=row.location[1],
                                location=row.location)

            # add DB references
            self._db_key = DBRef(Namespace.sgd, row.id)
            record.addDBRef(self._db_key)

            # add systematic name (= location) as a symbol
            if row.symbol:
                record.addSymbol(row.location)

            # add gene length as a keyword
            if row.length:
                 record.addKeyword(row.length)

            # add protein names as alternative symbol names
            if row.protein_name:
                record.addSymbol(row.protein_name)

            # stack the record (multiple alias lines!)
            self._record = record

        if row.alias and row.alias not in (row.symbol, row.name, row.location):
            if " " in row.alias and len(row.alias) > 8:
                self._record.addName(row.alias)
            else:
                self._record.addSymbol(row.alias)

        return count

    def _cleanup(self, file:io.TextIOWrapper) -> int:
        records = super(Parser, self)._cleanup(file)

        if self._record is not None:
            self._loadRecord(self._db_key, self._record)
            records += 1

        return records
