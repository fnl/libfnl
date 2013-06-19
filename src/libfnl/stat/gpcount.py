"""
.. py:module:: genecount
   :synopsis: Count the number of times a symbol appears in MEDLINE.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
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
    sym2gid = defaultdict(list)

    gnamed = GnamedSession()

    for sym, gid in gnamed.query(GeneString.value, GeneString.id
    ).filter(GeneString.cat == 'symbol'):
        sym2gid[sym].append(gid)

    gnamed = GnamedSession()

    for sym, gid in gnamed.query(ProteinString.value, Gene.id
    ).join(Gene.proteins
    ).join(ProteinString
    ).filter(ProteinString.cat == 'symbol'):
        sym2gid[sym].append(gid)

    _count(sym2gid)


def CountProteins():
    """
    Print the number of times each protein ID, symbol pair appears in all
    MEDLINE abstracts and the number of times it appears in referenced
    abstracts only.

    This produces a table with the format:
    PID <tab> SYMBOL <tab> NUM_ALL <tab> NUM_REF
    """
    sym2pid = defaultdict(list)

    gnamed = GnamedSession()

    for sym, pid in gnamed.query(ProteinString.value, ProteinString.id
    ).filter(ProteinString.cat == 'symbol'):
        sym2pid[sym].append(pid)

    gnamed = GnamedSession()

    for sym, pid in gnamed.query(GeneString.value, Protein.id
    ).join(Protein.genes
    ).join(GeneString
    ).filter(GeneString.cat == 'symbol'):
        sym2pid[sym].append(pid)

    _count(sym2pid)


def _count(sym2_id):
    pmid2sym = defaultdict(set)
    dwag = DAWG(sym2_id.keys())
    globalCounters = defaultdict(lambda: defaultdict(int))
    refCounters = defaultdict(lambda: defaultdict(int))

    gnamed = GnamedSession()

    for pmid, sym in gnamed.query(Gene2PubMed.pmid, GeneString.value
    ).join(GeneString, GeneString.id == Gene2PubMed.id):
        pmid2sym[pmid].add(sym)

    gnamed = GnamedSession()

    for pmid, sym in gnamed.query(Protein2PubMed.pmid, ProteinString.value
    ).join(ProteinString, ProteinString.id == Protein2PubMed.id):
        pmid2sym[pmid].add(sym)

    for pmid, symbols in pmid2sym.items():
        medline = MedlineSession()

        for txt in medline.query(Section.content
        ).filter(Section.pmid == pmid
        ).filter(Section.name != 'Copyright'
        ).filter(Section.name != 'Vernacular'):
            offsets = set(TokenOffsets(txt))

            # only attempt prefix matches at offsets
            for idx in offsets:
                keys = dwag.prefixes(txt, idx)

                if keys:
                    sym = keys[-1]

                    # only offset-delimited matches
                    if idx + len(sym) in offsets:
                        id_list = sym2_id[sym]

                        if sym in symbols:
                            for _id in id_list:
                                refCounters[_id][sym] += 1

                        for _id in id_list:
                            globalCounters[_id][sym] += 1

    for _id, global_counts in globalCounters.items():
        refCounts = refCounters[_id]

        for sym, count in global_counts.items():
            print("{}\t{}\t{}\t{}".format(_id, sym, count, refCounts[sym]))
