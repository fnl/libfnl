"""
.. py:module:: medline
   :synopsis: Download and parse MEDLINE XML records.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)

This module provides functions to fetch and parse NLM PubMed/MEDLINE XML
records, dump them into a CouchDB, and attach external content articles (eg.,
full-text articles) to them.
"""
import logging
import os
from collections import defaultdict
from io import StringIO
from http.client import HTTPResponse # function annotation only
from time import sleep, time, strptime
from unicodedata import normalize
from urllib.request import build_opener
from xml.etree.ElementTree import iterparse, tostring, Element
from logging import getLogger
from datetime import date, timedelta
from libfnl.couch.broker import Database
from libfnl.nlp.extract import Extract
from libfnl.nlp.text import Unicode

__all__ = ['Attach', 'Dump', 'Fetch', 'Parse']

LOGGER = getLogger()

MONTHS_SHORT = (None, 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
# to translate three-letter month strings to integers

URL_OPENER = build_opener()
# to avoid having to build a new opener for each request

EUTILS_URL = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?tool=libfnl&db=pubmed&retmode=xml&rettype=medline&id='
"""
The base URL where eUtils requests for MEDLINE records should be made.

Multiple PMIDs are joined comma-separated and appended to this URL.
"""

FETCH_SIZE = 100
"""
Number of records that can be fetched from eUtils in one request.
"""

SKIPPED_ELEMENTS = ('OtherID', 'OtherAbstract', 'SpaceFlightMission',
                    'GeneralNote', 'NameID', 'ELocationID', 'CitationSubset')
'Ignored tags in MedlineCitation elements that are never parsed.'

ABSTRACT_ELEMENTS = [
    ('ArticleTitle', 'title'),
    ('AbstractText', 'abstract'),
    ('Background', 'background'),
    ('Objective', 'objective'),
    ('Methods', 'methods'),
    ('Results', 'results'),
    ('Conclusions', 'conclusions'),
    ('CopyrightNotice', 'copyright')
]
"""
List of keys found in Article{1}->Abstract{0,1}, in order of how they should
be presented.
"""

ABSTRACT_FILE = 'abstract.txt'
"""
Name of file used for attaching abstracts to Couch documents.
"""

############
# IMPORTER #
############

def Dump(pmids:list([str]), db:Database, update:bool=False,
         force:bool=False) -> int:
    """
    :param pmids: The list of PMIDs to fetch (but existing articles will be
        ignored).
    :param db: A Couch :class:`.Database` instance.
    :param update: Update existing articles, if appropriate (see above).
    :param force: If ``True``, force the update of all existing articles.
    :return: Number of dumped documents.
    """
    last_access = 0.0
    processed_docs = 0

    for idx in range(0, len(pmids), FETCH_SIZE):
        if update:
            existing = { p: db[p] for p in pmids[idx:idx + FETCH_SIZE]
                         if p in db }
            if force:
                updated = existing
                query = pmids[idx:idx + FETCH_SIZE]
            else:
                updated = dict(filter(NeedsUpdate, existing.items()))
                query = [ p for p in pmids[idx:idx + FETCH_SIZE]
                          if (p in updated or p not in existing) ]
        else:
            updated = {}
            query = [ p for p in pmids[idx:idx + FETCH_SIZE] if p not in db ]

        if len(query):
            # the Gatekeeper: only make eUtils requests every 3 sec
            sleep(max(last_access - time() + 3, 0))
            last_access = time()
            processed_docs += len(query)
            stream = Fetch(query)
            db.bulk(MakeDocuments(stream, updated))

    return processed_docs


def NeedsUpdate(item:(str, dict)) -> bool:
    one_week = timedelta(7)
    today = date.today()
    doc = item[1]
    created = date(*strptime(doc['created'], '%Y-%m-%dT%H:%M:%S')[:3])

    if today - created < one_week:
        return False

    medline = doc['medline']

    if medline['Status'] in ('In-Data-Review', 'In-Process'):
        return True

    one_year = timedelta(365)
    created = date(*strptime(medline['DateCreated'], '%Y-%m-%d')[:3])

    if today - created > one_year:
        # select records that are one year old, but not more than ten
        if today - created < 10 * one_year:
            # ignoring 'ancient' records, check they have all three stamps
            for stamp in ('DateRevised', 'DateCompleted'):
                if stamp not in medline: return True
    else:
        # record is new, check if it has been completed
        if 'DateCompleted' not in medline:
            return True

    return False


def MakeDocuments(stream, old_revisions:dict=None) -> iter([dict]):
    """
    Parse MEDLINE records from an XML stream.

    The resulting iterator can simply be sent to :meth:`.couch.Database.bulk`
    to be inserted in a database. However, note that if you try to bulk load
    too many records at once, this might be rather dangerous. A few 100s or
    even up to about 10k records should not matter, although.

    :param stream: A readable, file-like object with the raw XML containing
        Medline Citations.
    :param old_revisions: A dictionary of CouchDB MEDLINE documents that are
        to be updated if found on the incoming XML stream. The dictionary's
        keys should be the PMIDs of the document, the values the document
        itself. Optional.
    :return: A document iterator.
    """
    for medline in Parse(stream):
        text = MakeUnicode(medline)
        text.metadata['medline'] = medline
        pmid = medline['PMID'][0]

        if old_revisions and pmid in old_revisions:
            pmid = old_revisions[pmid]

        yield text.toDocument(pmid)


def MakeUnicode(raw_json:dict) -> Unicode:
    article = raw_json['Article']
    title = normalize('NFC', article['ArticleTitle'])
    section_tags = {'title': [(0, len(title))]}

    if 'Abstract' in article:
        buffer = StringIO()
        buffer.write(title)
        text = TextFromAbstract(buffer, article['Abstract'], section_tags)
        del article['Abstract']
    else:
        text = title

    text = Unicode(text)
    text.tags = {'section': section_tags}
    return text


def TextFromAbstract(buffer:StringIO, abstract:dict, section_tags:dict) -> str:
    offset = section_tags['title'][0][1]

    for section, short in ABSTRACT_ELEMENTS:
        if section in abstract:
            buffer.write('\n\n')
            offset += 2
            content = normalize('NFC', abstract[section])
            start = offset
            offset += len(content)
            section_tags[short] = [(start, offset)]
            buffer.write(content)

    return buffer.getvalue()

##############
# DOWNLOADER #
##############

def Fetch(pmids:list, timeout:int=60) -> HTTPResponse:
    """
    :param pmids: a list of up to 100 PMIDs, as values that can be cast to
        string.
    :param timeout: Number of seconds to wait for a response.
    :return: An XML stream.
    :raises IOError: If the stream from eUtils cannot be opened.
    :raises urllib.error.URLError: If the connection to the eUtils URL cannot
        be made.
    :raises socket.timout: If *timeout* seconds have passed before a response
        arrives.
    """
    assert len(pmids) <= FETCH_SIZE, 'too many PMIDs'
    url = EUTILS_URL + ','.join(map(str, pmids))
    LOGGER.debug('fetching MEDLINE records from %s', url)
    return URL_OPENER.open(url, timeout=timeout)

##########
# PARSER #
##########

def Parse(xml_stream) -> iter([dict]):
    """
    :param xml_stream: A stream as returned by :func:`.Fetch`.
    :raise AssertionError: If parsing of the XML does not go as expected, but
        only in non-optimized mode.
    """
    for unused_event, element in iterparse(xml_stream):
        if element.tag == 'PubmedArticle':
            record = ParseElement(element.find('MedlineCitation'))
            article_id_list = element.find('PubmedData/ArticleIdList')

            if article_id_list is not None:
                record['ArticleIds'] = ParseArticleIdList(article_id_list)

            assert 'PMID' in record, \
                'No PMID in record XML:\n{}'.format(tostring(element))

            yield record

# Main Element Parser and Regular Elements

def ParseElement(element):
    tag = element.tag

    if tag.endswith('List'):
        return ParseElementList(element)
    elif tag.startswith('Date') or tag.endswith('Date'):
        return ParseDateElement(element)
    elif tag == 'MeshHeading':
        return ParseMeshHeading(element)
    elif tag == 'Abstract':
        return ParseAbstract(element)
    elif tag == 'PMID':
        LOGGER.debug('parsing PMID=%s', element.text)
        return element.text.strip(), int(element.get('Version', 1))
    elif tag == 'ISSN':
        return element.get('IssnType'), element.text.strip()
    else:
        return ParseRegularElement(element)


def ParseRegularElement(element):
    content = dict(ParseChildren(element))
    attributes = dict(element.items())

    if not content and not attributes:
        return element.text.strip()

    if attributes and not content:
        if len(attributes) == 1 and list(attributes.keys())[0].endswith('YN'):
            return element.text.strip()

        # done everything possible to avoid it...
        # without further options, put the element inside itself
        content[element.tag] = element.text.strip()


    if attributes: content.update(dict(attributes))
    assert content, 'Empty element; XML:\n{}'.format(tostring(element))
    return content


def ParseChildren(parent):
    known_tags = []

    for child in parent.getchildren():
        if child.tag in SKIPPED_ELEMENTS: continue

        if child.tag == 'ArticleDate':
            # Multiple article dates can exist; to avoid overwriting any,
            # use the DateType attribute as prefix of the tag/key.
            # The default, according to the DTD, is 'Electronic'.
            tag = '{}ArticleDate'.format(child.get('DateType', 'Electronic'))
        else:
            tag = child.tag

        assert tag not in known_tags, \
            'Duplicate child {}; XML::\n{}'.format(tag, tostring(parent))
        yield tag, ParseElement(child)
        known_tags.append(tag)


def ParseElementList(list_element:Element):
    return [ ParseElement(element) for element in list_element.getchildren() ]


def ParseDateElement(date_element):
    if date_element.tag == 'MedlineDate':
        return date_element.text.strip()
    try:
        year = int(date_element.find('Year').text)
        month_text = date_element.find('Month').text.strip()
        try:
            month = int(month_text)
        except ValueError:
            month = MONTHS_SHORT.index(month_text.lower())

        try:
            day = int(date_element.find('Day').text)
            return date(year, month, day)
        except (AttributeError, ValueError):
            return date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        if date_element.find('MedlineDate') is None:
            msg = 'ParseDateElement: %s not recognized; XML:\n%s'
            LOGGER.warn(msg, date_element.tag, tostring(date_element).strip())

        return dict(ParseChildren(date_element))

# Special Cases

def ParseArticleIdList(element):
    articles = {}

    for article in element.findall('ArticleId'):
        id_type = article.get('IdType')

        if id_type in articles:
            msg = 'duplicate {} ArticleId'.format(id_type)
            LOGGER.error(msg)
            assert id_type not in articles, \
                '{}; XML:\n{}'.format(msg, tostring(element))

        articles[id_type] = article.text.strip()

    assert articles, 'Empty ArticleIdList; XML:\n{}'.format(tostring(element))
    return articles


def ParseMeshHeading(element):
    ParseMesh = lambda e: (e.text.strip(), e.get('MajorTopicYN') == 'Y')

    descriptor = ParseMesh(element.find('DescriptorName'))
    qualifiers = dict(ParseMesh(e) for e in element.findall('QualifierName'))
    mesh_heading = (descriptor[1], descriptor[0], qualifiers)
    return mesh_heading


def ParseAbstract(element):
    abstract = {}

    for abstract_text in element.findall('AbstractText'):
        cat = abstract_text.get('NlmCategory', 'UNLABELLED').capitalize()

        if cat == 'Unlabelled': cat = 'AbstractText'
        assert cat not in abstract, \
            'Duplicate AbstractText NlmCategories; XML:\n' \
            '{}'.format(tostring(element))
        abstract[cat] = abstract_text.text.strip()

    copyright = element.find('CopyrightInformation')

    if copyright is not None:
        abstract['CopyrightInformation'] = copyright.text.strip()

    return abstract

#############
# RELATIONS #
#############

def Attach(filenames:list, medline_db:Database, encoding:str='utf-8',
           force:bool=False):
    """
    :param filenames: A list of file name strings.
    :param medline_db: A :class:`.Database` instance.
    :param encoding: The (charset) encoding of the files to attach.
    :param force: Replace any existing article. Note this does not erase any
        ``pmids`` already stored on the article.
    :raise IOError: If the file cannot be read.
    :return: A dictionary of PMIDs, with a list of the files' document IDs that
        were created for them.
    """
    logger = logging.getLogger('Attach')
    results = defaultdict(list)

    for fn in filenames:
        try:
            text = Extract(fn, encoding).toBinary('utf-8')
        except IOError:
            logger.error('could not read %s', fn)
            continue
        except RuntimeError:
            logger.exception('failed to extract %s', fn)
            continue

        base = os.path.basename(fn)
        pmid, ext = os.path.splitext(base)

        if pmid not in medline_db:
            logger.error('PMID %s not in DB', pmid)
            continue

        text_id = text.base64digest

        if text_id in medline_db:
            article = medline_db[text_id]
            pm_ids = article['pmids'] if 'pmids' in article else []

            if pmid in pm_ids and not force:
                logger.info('%s already attached', fn)
            else:
                pm_ids.append(pmid)
                text.metadata['pmids'] = pm_ids

                if force:
                    logger.info('overwriting %s (%s)', text_id, base)
                    article = text.toDocument(text_id)
                else:
                    logger.debug('updating %s with %s', text_id, base)
                    article = text.toDocument(article)

                medline_db[text_id] = article
        else:
            logger.debug('adding article %s (%s)', base, text_id)
            text.metadata['pmids'] = [pmid]
            article =  text.toDocument()
            medline_db[text_id] = article

        medline_db.saveAttachment(article, fn, 'raw.{}'.format(ext),
                                  charset=encoding)
        results[pmid].append(text_id)

    return results
