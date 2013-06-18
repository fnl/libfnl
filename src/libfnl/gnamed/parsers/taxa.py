"""
.. py:module:: libfnl.gnamed.parsers.taxa
   :synopsis: A parser for the NCBI Taxon names, nodes, and merged .dmp files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from collections import defaultdict
import logging
import io

from libfnl.gnamed.orm import Species, SpeciesName
from libfnl.gnamed.parsers import AbstractParser

class Parser(AbstractParser):
    """
    A parser for NCBI Taxonomy name records.

    Implements the `AbstractParser._parse` method.

    As loading species is trivial, but special, it has its own DB loading
    mechanism instead of relying on the `AbstractLoader` implementation.
    """

    def _setup(self, file:io.TextIOWrapper) -> int:
        lines = super(Parser, self)._setup(file)
        self._fileno = self._fileno + 1 if hasattr(self, '_fileno') else 1
        self._on_hold = defaultdict(list)
        self._loaded = set()

        if self._fileno == 1:
            self._taxa_map = dict()
            self._root_found = False
            logging.debug('parsing nodes')
            self._parse = self._parseNodes
        elif self._fileno == 2:
            logging.debug('parsing names')
            self._parse = self._parseNames
            self._current_names = set()
        elif  self._fileno == 3:
            logging.debug('parsing merged')
            self._parse = self._parseMerged
        else:
            raise RuntimeError('unexpected file ' + file.name)

        return lines

    def _loadRecursion(self, tax_id:int):
        records = self._on_hold.pop(tax_id)
        self.session.add_all(records)
        self._loaded.update(r.id for r in records)

        for r in records:
            logging.debug("storing %s", r.id)

            if r.id in self._on_hold:
                self._loadRecursion(r.id)

    def _parseNodes(self, line:str) -> int:
        items = [i.strip() for i in line.split('|')]
        assert len(items) == 14, line

        if not self._root_found and items[0] == items[1]:
            items[1] = None
            items[2] = 'root'
            self._root_found = True
        else:
            items[1] = int(items[1])

        self._taxa_map[int(items[0])] = (items[1], items[2])
        return 1

    def _parseNames(self, line:str) -> int:
        items = [i.strip() for i in line.split('|')]
        assert len(items) == 5, line
        species_id = int(items[0])

        if species_id != self.current_id:
            if self.record:
                if self.record.parent_id in self._loaded or \
                                self.record.parent_id is None:
                    logging.debug("storing %s", self.current_id)
                    self.session.add(self.record)
                    self._loaded.add(self.current_id)

                    if self.current_id in self._on_hold:
                        self._loadRecursion(self.current_id)
                else:
                    self._on_hold[self.record.parent_id].append(
                        self.record
                    )

            parent_id, rank = self._taxa_map[species_id]
            logging.debug('building %s->%s "%s"',
                          species_id, parent_id, rank)
            self.record = Species(species_id, parent_id, rank)
            self.current_id = species_id
            self._current_names = set()

        if items[3] == 'scientific name':
            assert not self.record.unique_name, \
                (self.record.unique_name, 'vs', items[1])

            if items[2]:
                self.record.unique_name = items[2]
            else:
                self.record.unique_name = items[1]
        elif items[3] == 'genbank common name':
            assert not self.record.genbank_name, \
                (self.record.genbank_name, 'vs', items[1])
            self.record.genbank_name = items[1]

        name = (items[3], items[1])

        if name not in self._current_names:
            self.record.names.append(
                SpeciesName(species_id, items[3], items[1])
            )
            self._current_names.add(name)

        return 1

    def _parseMerged(self, line:str) -> int:
        items = [i.strip() for i in line.split('|')]
        assert len(items) == 3, line
        species_id, parent_id = int(items[0]), int(items[1])
        self.record = Species(species_id, parent_id, 'merged')
        self.record.unique_name = 'species:{}'.format(parent_id)
        self.session.add(self.record)
        return 1

    def _flush(self):
        self.session.flush()

    def _cleanup(self, file:io.TextIOWrapper) -> int:
        num_records = super(Parser, self)._cleanup(file)

        if self.record:
            self.session.add(self.record)

        if len(self._on_hold):
            if self.record.id in self._on_hold:
                self._loadRecursion(self.record.id)

            if len(self._on_hold):
                # very, very bad - but try to add all, nonetheless
                logging.warn('could not load all tree dependencies in order')

                for records in self._on_hold.values():
                    self.session.add_all(records)

        return num_records
