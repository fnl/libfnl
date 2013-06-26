"""
.. py:module:: genecount
   :synopsis: Count the number of times a symbol appears in MEDLINE.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
from dawg import DAWG
from collections import defaultdict
from libfnl.gnamed.orm import Session as GnamedSession, GeneString, Gene, ProteinString, Gene2PubMed, Protein2PubMed, Protein
from libfnl.medline.orm import Session as MedlineSession, Section
from libfnl.text.strtok import TokenOffsets


def CountGenes():
    """
    Print the number of times each gene ID, symbol pair appears in all MEDLINE
    abstracts and the number of times it appears in referenced abstracts only.

    This produces a table with the format:
    GID <tab> SYMBOL <tab> NUM_ALL <tab> NUM_REF
    """
    sym2gid = defaultdict(set)
    pmid2gid = defaultdict(set)
    gnamed = GnamedSession()

    logging.info("loading gene symbol to id map")
    for sym, gid in gnamed.query(GeneString.value, GeneString.id
    ).filter(GeneString.cat == 'symbol').yield_per(100):
        sym2gid[sym].add(gid)

    logging.info("loading protein symbol to id map")
    for sym, gid in gnamed.query(ProteinString.value, Gene.id
    ).join(Gene.proteins).join(ProteinString).filter(ProteinString.cat == 'symbol').yield_per(100):
        sym2gid[sym].add(gid)

    logging.info("loading gene pmid to gene id map")
    for pmid, gid in gnamed.query(Gene2PubMed.pmid, Gene2PubMed.id).yield_per(100):
        pmid2gid[pmid].add(gid)

    logging.info("loading protein pmid to gene id map")
    for pmid, gid in gnamed.query(Protein2PubMed.pmid, Gene.id
    ).join(Gene.proteins).join(Protein2PubMed).yield_per(100):
        pmid2gid[pmid].add(gid)

    _count(sym2gid, pmid2gid)


def CountProteins():
    """
    Print the number of times each protein ID, symbol pair appears in all
    MEDLINE abstracts and the number of times it appears in referenced
    abstracts only.

    This produces a table with the format:
    PID <tab> SYMBOL <tab> NUM_ALL <tab> NUM_REF
    """
    sym2pid = defaultdict(set)
    pmid2pid = defaultdict(set)
    gnamed = GnamedSession()

    logging.info("loading protein symbol to id map")
    for sym, pid in gnamed.query(ProteinString.value, ProteinString.id
    ).filter(ProteinString.cat == 'symbol').yield_per(100):
        sym2pid[sym].add(pid)

    logging.info("loading gene symbol to id map")
    for sym, pid in gnamed.query(GeneString.value, Protein.id
    ).join(Protein.genes).join(GeneString).filter(GeneString.cat == 'symbol').yield_per(100):
        sym2pid[sym].add(pid)

    logging.info("loading protein pmid to gene id map")
    for pmid, pid in gnamed.query(Protein2PubMed.pmid, Protein2PubMed.id).yield_per(100):
        pmid2pid[pmid].add(pid)

    logging.info("loading gene pmid to gene id map")
    for pmid, pid in gnamed.query(Gene2PubMed.pmid, Protein.id
    ).join(Protein.genes).join(Gene2PubMed).yield_per(100):
        pmid2pid[pmid].add(pid)

    _count(sym2pid, pmid2pid)


def _count(sym2_id:defaultdict(set), pmid2_id:defaultdict(set)):
    # pruning: remove the "empty" symbol
    if '' in sym2_id:
        del sym2_id['']

    logging.info("initalizing counters")
    symbols = {s: 0 for s in sym2_id.keys()} # global count per symbol
    references = {} # count per id & symbol in the referenced titles

    for sym, ids in sym2_id.items():
        for id_ in ids:
            if id_ in references:
                references[id_][sym] = 0
            else:
                references[id_] = {sym: 0}

    logging.info("initializing DAFSA graph")
    dwag = DAWG(sym2_id.keys())
    medline = MedlineSession()

    for pmid, known_ids in pmid2_id.items():
        logging.info("counting PMID %d", pmid)
        relevant = {} # checked symbols

        while True:
            try:
                for (txt,) in medline.query(Section.content
                ).filter(Section.pmid == pmid
                ).filter(Section.name != 'Copyright'
                ).filter(Section.name != 'Vernacular'
                ):
                    offsets = set(TokenOffsets(txt))

                    # only attempt prefix matches at offsets
                    for idx in offsets:
                        keys = dwag.prefixes(txt[idx:])

                        if keys:
                            sym = keys[-1]

                            # only offset-delimited matches
                            if idx + len(sym) in offsets:
                                symbols[sym] += 1

                                if sym in relevant:
                                    if relevant[sym]:
                                        for id_ in known_ids & sym2_id[sym]:
                                            references[id_][sym] += 1
                                else:
                                    relevant[sym] = False

                                    for id_ in known_ids & sym2_id[sym]:
                                        references[id_][sym] += 1
                                        relevant[sym] = True
                break
            except DatabaseError:
                medline = MedlineSession()

    for _id, counts in references.items():
        for sym, count in counts.items():
            print("{}\t{}\t{}\t{}".format(_id, repr(sym)[1:-1], count, symbols[sym]))
