"""
.. py:module:: libmedlinedb.parser
   :synopsis: An ORM parser for MEDLINE XML records.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

import logging
from xml.etree.ElementTree import iterparse
from datetime import date

import re
from libfnl.medline.orm import \
    Identifier, Author as Author_, Qualifier, Descriptor, Section, Medline


__ALL__ = ['Parse']

MONTHS_SHORT = (None, 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
# to translate three-letter month strings to integers

def Parse(xml_stream, pubmed=False) -> iter:
    """
    :param xml_stream: A stream as returned by :func:`.Download` or the XML
        found in the MEDLINE distribution XML files.
    :param pubmed: ``True`` if parsing eUtils PubMed XML, not MEDLINE XML

    :return: an iterator over Medline ORM instances
    """
    pmid = -1
    seq = 0
    num = 0
    sub = 0
    pos = 0
    namespaces = set()
    make = {}

    def dispatch(f):
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
        nonlocal seq
        seq += 1
        return Section(pmid, seq, 'Title', element.text.strip())

    @dispatch
    def VernacularTitle(element):
        nonlocal seq
        seq += 1
        return Section(pmid, seq, 'Vernacular', element.text.strip())

    @dispatch
    def AbstractText(element):
        nonlocal seq
        seq += 1
        section = element.get('NlmCategory', 'Abstract').capitalize()
        return Section(
            pmid, seq, section, element.text.strip(), element.get('Label', None)
        )

    @dispatch
    def CopyrightInformation(element):
        nonlocal seq
        seq += 1
        return Section(pmid, seq, 'Copyright', element.text.strip())

    @dispatch
    def DescriptorName(element):
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
        pos += 1
        for child in element.getchildren():
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
            else:
                logging.warning('unknown Author element %s "%s"', child.tag, text)
        if initials == forename and initials is not None:
            # prune the repetition of initials in the forename field
            forename = None
        return Author_(pmid, pos, name, initials, forename, suffix)

    @dispatch
    def ELocationID(element):
        ns = element.get('EIdType').strip().lower()
        if ns not in namespaces:
            namespaces.add(ns)
            return Identifier(pmid, ns, element.text.strip())
        else:
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
        ns = element.get('IdType').strip().lower()
        text = element.text.strip()
        instance = None

        if ns in namespaces:
            if re.match('\d[\d\.]+\/.+', element.text.strip()) and \
                            'doi' not in namespaces:
                namespaces.add('doi')
                instance = Identifier(pmid, 'doi', text)
            else:
                logging.warning('duplicate %s identifier "%s"', ns, text)
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
        journal = element.find('MedlineJournalInfo').find('MedlineTA').text.strip()
        status = element.get('Status')
        if not pubmed:
            element.clear()
            pmid = -1
        return Medline(p, status, journal, **dates)

    # === MAIN PARSER LOOP ===
    logging.debug("parsing input stream")
    for _, element in iterparse(xml_stream):
        if element.tag == 'PMID' and pmid == -1:
            pmid = int(element.text)
            logging.debug("PMID %i", pmid)
            namespaces = set()
            seq = 0
            num = 0
            sub = 0
            pos = 0
        elif element.tag in make:
            instance = make[element.tag](element)
            if instance is not None:
                logging.debug("parsed %s", element.tag)
                yield instance
    # ========================

def ParseDate(date_element):
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
