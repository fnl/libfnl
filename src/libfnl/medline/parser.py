"""
.. py:module:: libmedlinedb.parser
   :synopsis: An ORM parser for MEDLINE XML records.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

import logging
import sys
import types
from xml.etree.ElementTree import iterparse
from datetime import date

import re
from libfnl.medline.orm import \
    Author, Chemical, Database, Descriptor, Identifier, Medline, Qualifier, Section

__ALL__ = ['MedlineXMLParser', 'PubMedXMLParser']

MONTHS_SHORT = (None, 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
# to translate three-letter month strings to integers

logger = logging.getLogger(__name__)

class State:
    UNDEFINED = 0
    PARSING = 1
    SKIPPING = -1


class Parser:
    """A basic parser implementation for NLM XML citations."""

    def __init__(self, unique=True):
        """
        Create a new parser.

        :param unique: if `True`, citations with VersionID != "1" are skipped
        """
        logging.basicConfig(level=logging.WARNING)
        print("log message:", file=sys.stderr)
        logger.info('configuring a %sunique parser', "" if unique else "non-")
        logger.error('wtf')
        self.unique = unique
        self.events = ('start', 'end') if unique else None
        logger.debug('state: UNDEFINED')
        self._state = State.UNDEFINED
        self.pmid = -1

    def reset(self, pmid):
        self.pmid = pmid

    def skipping(self):
        logger.debug('state: SKIPPING')
        self._state = State.SKIPPING

    def isSkipping(self):
        return State.SKIPPING == self._state

    def undefined(self):
        logger.debug('state: UNDEFINED')
        self._state = State.UNDEFINED

    def isUndefined(self):
        return State.UNDEFINED == self._state

    def parsing(self):
        logger.debug('state: PARSING')
        self._state = State.PARSING

    def isParsing(self):
        return State.PARSING == self._state

    def parse(self, xml_stream):
        for event, element in iterparse(xml_stream, self.events):
            if event == 'start':
                self.startElement(element)
            else:
                for instance in self.yieldInstances(element):
                    yield instance

    def startElement(self, element):
        if self.unique and element.tag == 'MedlineCitation':
            version = element.get('VersionID')

            if version is not None and version.strip() != "1":
                logger.info('detected a citation with VersionID "%s"', version)
                self.skipping()

    def yieldInstances(self, element):
        if element.tag == 'PMID':
            self.PMID(element)
        elif not self.isSkipping() and hasattr(self, element.tag):
            logger.debug('processing %s: %s', element.tag, repr(element.text))
            instance = getattr(self, element.tag)(element)

            if instance is not None:
                logger.debug('parsed %s', element.tag)

                if type(instance) is types.GeneratorType:
                    for i in instance:
                        yield i
                else:
                    yield instance
            else:
                logger.debug('ignored %s', element.tag)

    def MedlineCitation(self, element):
        dates = {}

        for name, key in (('DateCompleted', 'completed'),
                          ('DateCreated', 'created'),
                          ('DateRevised', 'revised')):
            e = element.find(name)

            if e is not None:
                dates[key] = ParseDate(e)

        status = element.get('Status')
        journal = element.find('MedlineJournalInfo').find('MedlineTA').text.strip()
        return Medline(self.pmid, status, journal, **dates)

    def PMID(self, element):
        pmid = int(element.text)

        if self.isUndefined():
            logger.debug('parsing PMID %i', pmid)
            self.reset(pmid)
            self.parsing()
        elif self.isParsing():
            logger.debug('another PMID %i', pmid)
        elif self.isSkipping():
            logger.info('skipping PMID %i', pmid)
        else:
            logger.error('unknown state %i', self._state)


class MedlineXMLParser(Parser):
    """A parser for (offline) MEDLINE XML (files)."""

    def __init__(self, *args, **kwargs):
        super(MedlineXMLParser, self).__init__(*args, **kwargs)
        logger.info('configuring a Medline parser')
        self.seq = 0
        self.num = 0
        self.sub = 0
        self.pos = 0
        self.chem = 0
        self.namespaces = None

    def reset(self, pmid):
        super(MedlineXMLParser, self).reset(pmid)
        self.seq = 0
        self.num = 0
        self.sub = 0
        self.pos = 0
        self.chem = 0
        self.namespaces = set()

    def AbstractText(self, element):
        # sometimes there are non-content AbstractText
        # elements in MEDLINE/PubMed ("<AbstractText/>")
        if element.text is not None:
            text = element.text.strip()
            # and, less frequently, they might only contain whitespaces
            if text:
                self.seq += 1
                section = element.get('NlmCategory', 'Abstract').capitalize()
                return Section(
                    self.pmid, self.seq, section, text, element.get('Label', None)
                )

        logger.info('empty %s AbstractText in %i',
                         element.get('NlmCategory', 'ABSTRACT'), self.pmid)
        return None

    def ArticleTitle(self, element):
        if element.text is not None:
            self.seq += 1
            return Section(self.pmid, self.seq, 'Title', element.text.strip())

    def Author(self, element):
        name, forename, initials, suffix = self.parseAuthorElements(element.getchildren())

        if initials == forename and initials is not None:
            # prune the repetition of initials in the forename
            forename = None

        if name is not None:
            self.pos += 1
            return Author(self.pmid, self.pos, name, initials, forename, suffix)
        else:
            logger.warning('empty or missing Author/LastName or CollectiveName in %i', self.pmid)
            return None

    def parseAuthorElements(self, children):
        name, forename, initials, suffix = None, None, None, None

        for child in children:
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
                    initials = ''
                    suffix = ''
                elif child.tag == 'Identifier':
                    pass
                elif child.tag == 'Affiliation':
                    pass
                else:
                    logger.warning('unknown Author element %s "%s" in %i', child.tag, text, self.pmid)
            else:
                logger.warning('empty Author element %s in %i"', child.tag, self.pmid)

        return name, forename, initials, suffix

    def Chemical(self, element):
        self.chem += 1
        e = element.find('RegistryNumber')
        uid = None

        if e is not None and e.text is not None and e.text.strip() != "0":
            uid = e.text.strip()

        name = element.find('NameOfSubstance')
        return Chemical(self.pmid, self.chem, uid, name.text.strip())

    def CopyrightInformation(self, element):
        if element.text is not None:
            self.seq += 1
            return Section(self.pmid, self.seq, 'Copyright', element.text.strip())

    def DataBank(self, element):
        name = element.find('DataBankName')

        if name is not None and name.text:
            done = set()

            for acc in element.find('AccessionNumberList').getchildren():
                if acc.text and acc.text not in done:
                    done.add(acc.text)
                    yield Database(self.pmid, name.text, acc.text)

    def DescriptorName(self, element):
        if element.text is not None:
            self.num += 1
            self.sub = 0
            return Descriptor(
                self.pmid, self.num, element.text.strip(),
                (element.get('MajorTopicYN', 'N') == 'Y')
            )

    def QualifierName(self, element):
        if element.text is not None:
            self.sub += 1
            return Qualifier(
                self.pmid, self.num, self.sub, element.text.strip(),
                (element.get('MajorTopicYN', 'N') == 'Y')
            )

    def ELocationID(self, element):
        ns = element.get('EIdType').strip().lower()

        if ns not in self.namespaces:
            self.namespaces.add(ns)
            return Identifier(self.pmid, ns, element.text.strip())

        return None

    def MedlineCitation(self, element):
        instance = Parser.MedlineCitation(self, element)
        element.clear()
        self.undefined()
        return instance

    def OtherID(self, element):
        if element.get('Source', None) == 'NLM':
            text = element.text.strip()

            if text.startswith('PMC'):
                if 'pmc' not in self.namespaces:
                    self.namespaces.add('pmc')
                    return Identifier(self.pmid, 'pmc', text.split(' ', 1)[0])

        return None

    def VernacularTitle(self, element):
        if element.text is not None:
            self.seq += 1
            return Section(self.pmid, self.seq, 'Vernacular', element.text.strip())


class PubMedXMLParser(MedlineXMLParser):
    """A parser for PubMed (eUtils, online) XML."""

    def __init__(self, *args, **kwargs):
        super(PubMedXMLParser, self).__init__(*args, **kwargs)
        logger.info('configuring a PubMed parser')

    def PubmedArticle(self, element):
        element.clear()
        self.undefined()

    def ArticleId(self, element):
        instance = None
        ns = element.get('IdType').strip().lower()
        text = element.text.strip()

        if ns in self.namespaces:
            if re.match('\d[\d\.]+\/.+', element.text.strip()) and 'doi' not in self.namespaces:
                self.namespaces.add('doi')
                instance = Identifier(self.pmid, 'doi', text)
            else:
                logger.info('skipping duplicate %s identifier "%s"', ns, text)
        else:
            self.namespaces.add(ns)
            instance = Identifier(self.pmid, ns, text)

        return instance

    def MedlineCitation(self, element):
        # skip MedlineXMLParser-specific instructions:
        return Parser.MedlineCitation(self, element)


def ParseDate(date_element):
    """Parse a **valid** date that (at least) has to have a Year element."""
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

#def Parse(xml_stream, pubmed, uniq=False) -> iter:
#    """
#    :param xml_stream: A stream as returned by :func:`.Download` or the XML
#        found in the MEDLINE distribution XML files.
#    :param pubmed: ``True`` if parsing eUtils PubMed XML, not MEDLINE XML
#    :param uniq: ``True`` if citations with VersionID != "1" should be skipped
#
#    :return: an iterator over Medline ORM instances
#    """
#    pmid = -1 # -1 => outside record; -2 => skipping record; otherwise => parsing
#    events = ['start', 'end'] if uniq else None
#    seq = 0
#    num = 0
#    sub = 0
#    pos = 0
#    chem = 0
#    namespaces = set()
#    make = {}
#
#    if not pubmed:
#        check = lambda element: element.tag == 'MedlineCitation'
#        logging.info('parsing Medline XML files')
#    else:
#        check = lambda element: element.tag == 'PubmedArticle'
#        logging.info('parsing PubMed XML stream')
#
#    def dispatch(f):
#        "Decorator to populate a dispatcher using the element tag as function name."
#        make[f.__name__] = f
#        return f
#
#    @dispatch
#    def PubmedArticle(element):
#        "Special case: parsing (eUtils) PubMed XML, not MEDLINE XML."
#        nonlocal pmid
#        element.clear()
#        pmid = -1
#
#    @dispatch
#    def ArticleTitle(element):
#        if element.text is not None:
#            nonlocal seq
#            seq += 1
#            return Section(pmid, seq, 'Title', element.text.strip())
#
#    @dispatch
#    def VernacularTitle(element):
#        if element.text is not None:
#            nonlocal seq
#            seq += 1
#            return Section(pmid, seq, 'Vernacular', element.text.strip())
#
#    @dispatch
#    def AbstractText(element):
#        # infrequently, there are non-content AbstractText elements
#        # in MEDLINE/PubMed ("<AbstractText/>"), so:
#        if element.text is not None:
#            nonlocal seq
#            text = element.text.strip()
#            # and even less frequently, they might only contain whitespaces, so:
#            if text:
#                seq += 1
#                section = element.get('NlmCategory', 'Abstract').capitalize()
#                return Section(
#                    pmid, seq, section, text, element.get('Label', None)
#                )
#        logging.info("empty %s AbstractText in %i",
#                     element.get('NlmCategory', 'ABSTRACT'), pmid)
#        return None
#
#    @dispatch
#    def Chemical(element):
#        nonlocal chem
#        chem += 1
#        e = element.find('RegistryNumber')
#
#        if e is not None and e.text is not None and e.text.strip() != "0":
#            uid = e.text.strip()
#        else:
#            uid = None
#
#        name = element.find('NameOfSubstance')
#        return Chemical_(pmid, chem, uid, name.text.strip())
#
#    @dispatch
#    def CopyrightInformation(element):
#        if element.text is not None:
#            nonlocal seq
#            seq += 1
#            return Section(pmid, seq, 'Copyright', element.text.strip())
#
#    @dispatch
#    def DescriptorName(element):
#        if element.text is not None:
#            nonlocal num
#            nonlocal sub
#            num += 1
#            sub = 0
#            return Descriptor(
#                pmid, num, element.text.strip(),
#                (element.get('MajorTopicYN', 'N') == 'Y')
#            )
#
#    @dispatch
#    def QualifierName(element):
#        if element.text is not None:
#            nonlocal sub
#            sub += 1
#            return Qualifier(
#                pmid, num, sub, element.text.strip(),
#                (element.get('MajorTopicYN', 'N') == 'Y')
#            )
#
#    @dispatch
#    def Author(element):
#        nonlocal pos
#        name = None
#        forename = None
#        initials = None
#        suffix = None
#
#        for child in element.getchildren():
#            if child.text is not None:
#                text = child.text.strip()
#                if child.tag == 'LastName':
#                    name = text
#                elif child.tag == 'ForeName':
#                    forename = text
#                elif child.tag == 'Initials':
#                    initials = text
#                elif child.tag == 'Suffix':
#                    suffix = text
#                elif child.tag == 'CollectiveName':
#                    name = text
#                    forename = ''
#                    initials = ''
#                    suffix = ''
#                elif child.tag == 'Identifier':
#                    pass
#                elif child.tag == 'Affiliation':
#                    pass
#                else:
#                    logging.warning('unknown Author element %s "%s" in %i', child.tag, text, pmid)
#            else:
#                logging.warning('empty Author element %s in %i"', child.tag, pmid)
#
#        if initials == forename and initials is not None:
#            # prune the repetition of initials in the forename
#            forename = None
#
#        if name is not None:
#            pos += 1
#            return Author_(pmid, pos, name, initials, forename, suffix)
#        else:
#            logging.warning("empty or missing Author/LastName or CollectiveName in %i", pmid)
#            return None
#
#    @dispatch
#    def ELocationID(element):
#        ns = element.get('EIdType').strip().lower()
#
#        if ns not in namespaces:
#            namespaces.add(ns)
#            return Identifier(pmid, ns, element.text.strip())
#
#        return None
#
#    @dispatch
#    def OtherID(element):
#        if element.get('Source', None) == 'NLM':
#            text = element.text.strip()
#
#            if text.startswith('PMC'):
#                if 'pmc' not in namespaces:
#                    namespaces.add('pmc')
#                    return Identifier(pmid, 'pmc', text.split(' ', 1)[0])
#
#        return None
#
#    @dispatch
#    def ArticleId(element):
#        "This element is only present in the online PubMed XML, not the MEDLINE XML."
#        instance = None
#        ns = element.get('IdType').strip().lower()
#        text = element.text.strip()
#
#        if ns in namespaces:
#            if re.match('\d[\d\.]+\/.+', element.text.strip()) and \
#                            'doi' not in namespaces:
#                namespaces.add('doi')
#                instance = Identifier(pmid, 'doi', text)
#            else:
#                logging.info('skipping duplicate %s identifier "%s"', ns, text)
#        else:
#            namespaces.add(ns)
#            instance = Identifier(pmid, ns, text)
#
#        return instance
#
#    @dispatch
#    def MedlineCitation(element):
#        nonlocal pmid
#        p = pmid
#        dates = {}
#        for name, key in (('DateCompleted', 'completed'),
#                          ('DateCreated', 'created'),
#                          ('DateRevised', 'revised')):
#            e = element.find(name)
#
#            if e is not None:
#                dates[key] = ParseDate(e)
#
#        status = element.get('Status')
#        journal = element.find('MedlineJournalInfo').find('MedlineTA').text.strip()
#
#        if not pubmed:
#            element.clear()
#            pmid = -1
#
#        return Medline(p, status, journal, **dates)
#
#    @dispatch
#    def DataBank(element):
#        nonlocal pmid
#        name = element.find('DataBankName')
#        if name is not None and name.text:
#            done = set()
#            for acc in element.find('AccessionNumberList').getchildren():
#                if acc.text and acc.text not in done:
#                    done.add(acc.text)
#                    yield Database(pmid, name.text, acc.text)
#
#
#    # === MAIN PARSER LOOP ===
#    for event, element in iterparse(xml_stream, events):
#        if event == 'start':
#            # check for non-unique (versioned) records
#            if uniq and element.tag == 'MedlineCitation':
#                version = element.get('VersionID')
#
#                if version is not None and version.strip() != "1":
#                    logging.info("skipping a non-unique, versioned citation")
#                    pmid = -2
#
#            continue # ignore other start events
#
#        if element.tag == 'PMID' and pmid == -1:
#            pmid = int(element.text)
#            logging.debug("parsing PMID %i", pmid)
#            namespaces = set()
#            seq = 0
#            num = 0
#            sub = 0
#            pos = 0
#            chem = 0
#        elif element.tag in make:
#            # pmid == -2 means skip this record
#            if pmid == -2:
#                if check(element):
#                    pmid = -1
#            else:
#                instance = make[element.tag](element)
#
#                if instance is not None:
#                    logging.debug("parsed %s", element.tag)
#
#                    if type(instance) is types.GeneratorType:
#                        for i in instance:
#                            yield i
#                    else:
#                        yield instance
#                    # ========================

