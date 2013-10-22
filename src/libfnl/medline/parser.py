"""
.. py:module:: libmedlinedb.parser
   :synopsis: An ORM parser for MEDLINE XML records.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

import logging
import types
from xml.etree.ElementTree import iterparse
from datetime import date

import re
from libfnl.medline.orm import \
    Chemical as Chemical_, Database, Identifier, Author as Author_, \
    Qualifier, Descriptor, Section, Medline


__ALL__ = ['Parse']

MONTHS_SHORT = (None, 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
# to translate three-letter month strings to integers


def Parse(xml_stream, pubmed, uniq=False) -> iter:
    """
    :param xml_stream: A stream as returned by :func:`.Download` or the XML
        found in the MEDLINE distribution XML files.
    :param pubmed: ``True`` if parsing eUtils PubMed XML, not MEDLINE XML
    :param uniq: ``True`` if citations with VersionID != "1" should be skipped

    :return: an iterator over Medline ORM instances
    """
    pmid = -1 # -1 => outside record; -2 => skipping record; otherwise => parsing
    events = ['start', 'end'] if uniq else None
    seq = 0
    num = 0
    sub = 0
    pos = 0
    chem = 0
    namespaces = set()
    make = {}

    if not pubmed:
        check = lambda element: element.tag == 'MedlineCitation'
        logging.info('parsing Medline XML files')
    else:
        check = lambda element: element.tag == 'PubmedArticle'
        logging.info('parsing PubMed XML stream')

    def dispatch(f):
        "Decorator to populate a dispatcher using the element tag as function name."
        make[f.__name__] = f
        return f

    @dispatch
    def PubmedArticle(element):
        "Special case: parsing (eUtils) PubMed XML, not MEDLINE XML."
        nonlocal pmid
        element.clear()
        pmid = -1

    @dispatch
    def ArticleTitle(element):
        if element.text is not None:
            nonlocal seq
            seq += 1
            return Section(pmid, seq, 'Title', element.text.strip())

    @dispatch
    def VernacularTitle(element):
        if element.text is not None:
            nonlocal seq
            seq += 1
            return Section(pmid, seq, 'Vernacular', element.text.strip())

    @dispatch
    def AbstractText(element):
        # infrequently, there are non-content AbstractText elements
        # in MEDLINE/PubMed ("<AbstractText/>"), so:
        if element.text is not None:
            nonlocal seq
            text = element.text.strip()
            # and even less frequently, they might only contain whitespaces, so:
            if text:
                seq += 1
                section = element.get('NlmCategory', 'Abstract').capitalize()
                return Section(
                    pmid, seq, section, text, element.get('Label', None)
                )
        logging.info("empty %s AbstractText in %i",
                     element.get('NlmCategory', 'ABSTRACT'), pmid)
        return None

    @dispatch
    def Chemical(element):
        nonlocal chem
        chem += 1
        e = element.find('RegistryNumber')

        if e is not None and e.text is not None and e.text.strip() != "0":
            uid = e.text.strip()
        else:
            uid = None

        name = element.find('NameOfSubstance')
        return Chemical_(pmid, chem, uid, name.text.strip())

    @dispatch
    def CopyrightInformation(element):
        if element.text is not None:
            nonlocal seq
            seq += 1
            return Section(pmid, seq, 'Copyright', element.text.strip())

    @dispatch
    def DescriptorName(element):
        if element.text is not None:
            nonlocal num
            nonlocal sub
            num += 1
            sub = 0
            return Descriptor(
                pmid, num, element.text.strip(),
                (element.get('MajorTopicYN', 'N') == 'Y')
            )

    @dispatch
    def QualifierName(element):
        if element.text is not None:
            nonlocal sub
            sub += 1
            return Qualifier(
                pmid, num, sub, element.text.strip(),
                (element.get('MajorTopicYN', 'N') == 'Y')
            )

    @dispatch
    def Author(element):
        nonlocal pos
        name = None
        forename = None
        initials = None
        suffix = None

        for child in element.getchildren():
            if child.text is not None:
                text = child.text.strip()
                if child.tag == 'LastName':
                    name = text
                elif child.tag == 'ForeName':
                    forename = text
                elif child.tag == 'Initials':
                    initials = text
                elif child.tag == 'Suffix':
                    suffix = text
                elif child.tag == 'CollectiveName':
                    name = text
                    forename = ''
                    initials= ''
                    suffix = ''
                elif child.tag == 'Identifier':
                    pass
                elif child.tag == 'Affiliation':
                    pass
                else:
                    logging.warning('unknown Author element %s "%s" in %i', child.tag, text, pmid)
            else:
                logging.warning('empty Author element %s in %i"', child.tag, pmid)

        if initials == forename and initials is not None:
            # prune the repetition of initials in the forename
            forename = None

        if name is not None:
            pos += 1
            return Author_(pmid, pos, name, initials, forename, suffix)
        else:
            logging.warning("empty or missing Author/LastName or CollectiveName in %i", pmid)
            return None

    @dispatch
    def ELocationID(element):
        ns = element.get('EIdType').strip().lower()

        if ns not in namespaces:
            namespaces.add(ns)
            return Identifier(pmid, ns, element.text.strip())

        return None

    @dispatch
    def OtherID(element):
        if element.get('Source', None) == 'NLM':
            text = element.text.strip()

            if text.startswith('PMC'):
                if 'pmc' not in namespaces:
                    namespaces.add('pmc')
                    return Identifier(pmid, 'pmc', text.split(' ', 1)[0])

        return None

    @dispatch
    def ArticleId(element):
        "This element is only present in the online PubMed XML, not the MEDLINE XML."
        instance = None
        ns = element.get('IdType').strip().lower()
        text = element.text.strip()

        if ns in namespaces:
            if re.match('\d[\d\.]+\/.+', element.text.strip()) and \
                            'doi' not in namespaces:
                namespaces.add('doi')
                instance = Identifier(pmid, 'doi', text)
            else:
                logging.info('skipping duplicate %s identifier "%s"', ns, text)
        else:
            namespaces.add(ns)
            instance = Identifier(pmid, ns, text)

        return instance

    @dispatch
    def MedlineCitation(element):
        nonlocal pmid
        p = pmid
        dates = {}
        for name, key in (('DateCompleted', 'completed'),
                          ('DateCreated', 'created'),
                          ('DateRevised', 'revised')):
            e = element.find(name)

            if e is not None:
                dates[key] = ParseDate(e)

        status = element.get('Status')
        journal = element.find('MedlineJournalInfo').find('MedlineTA').text.strip()

        if not pubmed:
            element.clear()
            pmid = -1

        return Medline(p, status, journal, **dates)

    @dispatch
    def DataBank(element):
        nonlocal pmid
        name = element.find('DataBankName')
        if name is not None and name.text:
            done = set()
            for acc in element.find('AccessionNumberList').getchildren():
                if acc.text and acc.text not in done:
                    done.add(acc.text)
                    yield Database(pmid, name.text, acc.text)


    # === MAIN PARSER LOOP ===
    for event, element in iterparse(xml_stream, events):
        if event == 'start':
            # check for non-unique (versioned) records
            if uniq and element.tag == 'MedlineCitation':
                version = element.get('VersionID')

                if version is not None and version.strip() != "1":
                    logging.info("skipping a non-unique, versioned citation")
                    pmid = -2

            continue # ignore other start events

        if element.tag == 'PMID' and pmid == -1:
            pmid = int(element.text)
            logging.debug("parsing PMID %i", pmid)
            namespaces = set()
            seq = 0
            num = 0
            sub = 0
            pos = 0
            chem = 0
        elif element.tag in make:
            # pmid == -2 means skip this record
            if pmid == -2:
                if check(element):
                    pmid = -1
            else:
                instance = make[element.tag](element)

                if instance is not None:
                    logging.debug("parsed %s", element.tag)

                    if type(instance) is types.GeneratorType:
                        for i in instance:
                            yield i
                    else:
                        yield instance
    # ========================

def ParseDate(date_element):
    "Parse a **valid** date that (at least) has to have a Year element."
    year = int(date_element.find('Year').text)
    month, day = 1, 1
    month_element = date_element.find('Month')
    day_element = date_element.find('Day')

    if month_element is not None:
        month_text = month_element.text.strip()
        try:
            month = int(month_text)
        except ValueError:
            logging.debug('non-numeric Month "%s"', month_text)
            try:
                month = MONTHS_SHORT.index(month_text.lower())
            except ValueError:
                logging.warning('could not parse Month "%s"', month_text)
                month = 1

    if day_element is not None:
        try:
            day = int(day_element.text)
        except (AttributeError, ValueError):
            logging.warning('could not parse Day "%s"', day_element.text)

    return date(year, month, day)
