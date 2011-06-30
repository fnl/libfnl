"""
.. py:module:: medline
   :synopsis: Download and parse MEDLINE XML records.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>

This module provides functions to fetch and parse NLM PubMed/MEDLINE XML
records, and dump them into a CouchDB.

A simple usage example:

>>> from libfnl.nlp.medline import * # imports only the next two functions
>>> for record in Parse(Fetch((11700088, 11748933))):
...     print("PMID", record["_id"], "Title:", record["Article"]["ArticleTitle"])
PMID 11700088 Title: Proton MRI of (13)C distribution by J and chemical shift editing.
PMID 11748933 Title: Is cryopreservation a homogeneous process? Ultrastructure and motility of untreated, prefreezing, and postthawed spermatozoa of Diplodus puntazzo (Cetti).
"""
from io import StringIO
from http.client import HTTPResponse # function annotation only
from time import sleep, time, strptime
from urllib.request import build_opener
from xml.etree.ElementTree import iterparse, tostring
from logging import getLogger
from datetime import date, timedelta
from libfnl.couch.broker import Database
from libfnl.nlp.text import Unicode, Binary

__all__ = ['Fetch', 'Parse']

LOGGER = getLogger()

MONTHS_SHORT = (None, "jan", "feb", "mar", "apr", "may", "jun",
                "jul", "aug", "sep", "oct", "nov", "dec")
# to translate three-letter month strings to integers

URL_OPENER = build_opener()
# to avoid having to build a new opener for each request

EUTILS_URL = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?tool=libfnl&db=pubmed&retmode=xml&rettype=medline&id="
"""
The base URL where eUtils requests for MEDLINE records should be made.

Multiple PMIDs are joined comma-separated and appended to this URL.
"""

FETCH_SIZE = 100
"""
Number of records that can be fetched from eUtils in one go.
"""

SKIPPED_ELEMENTS = ("OtherID", "OtherAbstract", "SpaceFlightMission",
                    "GeneralNote", "NameID", "ELocationID")
"Ignored tags in MedlineCitation elements that are never parsed."

ABSTRACT_ELEMENTS = ("AbstractText", "Background", "Objective", "Methods",
                     "Results", "Conclusions", "CopyrightNotice")
"""
List of keys found in Article{1}->Abstract{0,1}, in order of how they should
be presented.
"""

ABSTRACT_FILE = "abstract.txt"
"""
Name of file used for attaching abstracts to Couch documents.
"""

############
# IMPORTER #
############

def Dump(pmids:list([str]), db:Database, update:bool=False, force:bool=False):
    """
    Dump MEDLINE DB records for a given list of *PMIDs* into a Couch *DB*.

    Records are treated as :class:`libfnl.nlp.text.Binary` data by attaching
    the title and abstract (if present) to the document. The key **Abstract**
    in **Article** will be deleted.

    Records already existing in a MEDLINE CouchDB can be checked if they are
    ripe for *update*. This is the case if they are one to ten years old and
    do not have all three time stamps (created, completed, and revised) or if
    they are less than one year old and have no a **DateCompleted**.

    This "filtered" update mechanism can be overridden and the update can
    be *force*\ d for all existing records.

    :param pmids: The list of PMIDs to fetch (but existing articles will be
        ignored).
    :param db: A Couch :class:`.Database` instance.
    :param update: Update existing articles, if appropriate (see above).
    :param force: If ``True``, force the update of all existing articles.
    """
    last_access = 0.0

    for idx in range(0, len(pmids), FETCH_SIZE):
        if force:
            updated = { p: db[p].rev for p in pmids[idx:idx + FETCH_SIZE]
                        if p in db }
            query = pmids[idx:idx + FETCH_SIZE]
        elif update:
            existing = { p: db[p] for p in pmids[idx:idx + FETCH_SIZE]
                         if p in db }
            updated = dict(map(lambda p, d: (p, d.rev),
                               filter(NeedsUpdate, existing.items())))
            query = [ p for p in pmids[idx:idx + FETCH_SIZE]
                      if (p in updated or p not in existing) ]
        else:
            updated = {}
            query = [ p for p in pmids[idx:idx + FETCH_SIZE] if p not in db ]

        if len(query):
            # the Gatekeeper: only make eUtils requests every 3 sec
            sleep(max(last_access - time() + 3, 0))
            last_access = time()
            stream = Fetch(pmids[idx:idx + FETCH_SIZE])
            db.bulk(MakeDocuments(stream, updated))


def NeedsUpdate(item:(str, dict)) -> bool:
    one_year = timedelta(365)
    today = date.today()
    doc = item[1]
    created = date(*strptime(doc["DateCreated"], "%Y-%m-%d")[0:3])

    if today - created > one_year:
        # select records that are one year old, but not more than ten
        if today - created < 10 * one_year:
            # ignoring "ancient" records, check they have all three stamps
            for stamp in ("DateRevised", "DateCompleted"):
                if stamp not in doc: return True
    else:
        # record is new and might have not yet been completed
        if "DateCompleted" not in doc: return True

    return False


def MakeDocuments(stream, old_revisions:dict) -> iter([dict]):
    for raw_json in Parse(stream):
        text = MakeBinary(raw_json)

        if raw_json['_id'] in old_revisions:
            raw_json['_rev'] = old_revisions[raw_json['_id']]

        yield text.toDocument(raw_json, ABSTRACT_FILE)


def MakeBinary(raw_json:dict) -> Binary:
    title = raw_json["Article"]["ArticleTitle"]
    section_tags = {"ArticleTitle": [(0, len(title))]}
    abstract = raw_json["Article"].get("Abstract", None)

    if abstract:
        text = TextFromAbstract(StringIO(title), abstract, section_tags)
        del raw_json["Article"]["Abstract"]
    else:
        text = title

    text = Unicode(text)
    text.tags = {"section": section_tags}
    text = text.toBinary('utf-8')
    return text


def TextFromAbstract(buffer:StringIO, abstract:dict, section_tags:dict) -> str:
    offset = section_tags["ArticleTitle"][0][1]

    for section in ABSTRACT_ELEMENTS:
        if section in abstract:
            buffer.write("\n\n")
            offset += 2
            content = abstract[section]
            start = offset
            offset += len(content)
            section_tags[section] = [(start, offset)]
            buffer.write(content)

    return buffer.getvalue()

##############
# DOWNLOADER #
##############

def Fetch(pmids:list, timeout:int=60) -> HTTPResponse:
    """
    Open an XML stream from the NLM for a list of *PMIDs*, but at most 100
    (the approximate upper limit of IDs for this query to the eUtils API).

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
    assert len(pmids) <= FETCH_SIZE, "too many PMIDs"
    url = EUTILS_URL + ','.join(map(str, pmids))
    LOGGER.debug("fetching MEDLINE records from %s", url)
    return URL_OPENER.open(url, timeout=timeout)

##########
# PARSER #
##########

def Parse(xml_stream, pmid_key:str="_id") -> iter([dict]):
    """
    Yield MEDLINE records as dictionaries from an *XML stream*, with the
    **PMID** set as string value of the specified *PMID key* (default:
    **_id**).

    :param xml_stream: A stream as returned by :func:`.Fetch`.
    :param pmid_key: The dictionary key to store the PMID in.
    :raise AssertionError: If parsing of the XML does not go as expected, but
        only in non-optimized mode.
    """
    for unused_event, element in iterparse(xml_stream):
        if element.tag == "PubmedArticle":
            record = ParseElement(element.find("MedlineCitation"))
            article_id_list = element.find("PubmedData/ArticleIdList")

            if article_id_list is not None:
                record["ArticleIds"] = ParseArticleIdList(article_id_list)

            assert "PMID" in record, \
                "No PMID in record XML:\n{}".format(tostring(element))

            if isinstance(record["PMID"], str):
                record[pmid_key] = record["PMID"]
            else:
                record[pmid_key] = record["PMID"]["PMID"]

            yield record

# Main Element Parser and Regular Elements

def ParseElement(element):
    tag = element.tag

    if __debug__ and tag == "PMID":
        LOGGER.debug("Parse: PMID=%s", element.text)

    if tag.endswith("List"):
        return ParseElementList(element)
    elif tag.startswith("Date") or tag.endswith("Date"):
        return ParseDateElement(element)
    elif tag == "Abstract":
        return ParseAbstract(element)
    elif tag == "MeshHeading":
        return ParseMeshHeading(element)
    else:
        return ParseRegularElement(element)


def ParseRegularElement(element):
    content = dict(ParseChildren(element))
    attributes = element.items()

    if not content and not attributes:
        return element.text

    if attributes and not content:
        if element.tag in ("DescriptorName", "QualifierName"):
            # Special case for MeSH descriptors and qualifiers
            return element.text, element.get("MajorTopicYN") == "Y"

        content[element.tag] = element.text

    if attributes: content.update(dict(attributes))
    assert content, "Empty element; XML:\n{}".format(tostring(element))
    return content


def ParseChildren(parent):
    known_tags = []

    for child in parent.getchildren():
        if child.tag in SKIPPED_ELEMENTS: continue

        if child.tag == "ArticleDate":
            # Multiple article dates can exist; to avoid overwriting any,
            # use the DateType attribute as prefix of the tag/key.
            # The default, according to the DTD, is "Electronic".
            tag = "{}ArticleDate".format(child.get("DateType", "Electronic"))
        else:
            tag = child.tag

        assert tag not in known_tags, \
            "Duplicate child {}; XML::\n{}".format(tag, tostring(parent))
        yield tag, ParseElement(child)
        known_tags.append(tag)


def ParseElementList(list_element):
    return [ ParseElement(element) for element in list_element.getchildren() ]


def ParseDateElement(date_element):
    if date_element.tag == "MedlineDate":
        return date_element.text
    try:
        year = int(date_element.find("Year").text)
        month_text = date_element.find("Month").text
        try:
            month = int(month_text)
        except ValueError:
            month = MONTHS_SHORT.index(month_text.lower())

        try:
            day = int(date_element.find("Day").text)
            return date(year, month, day)
        except (AttributeError, ValueError):
            return date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        if date_element.find("MedlineDate") is None:
            msg = "ParseDateElement: {} not recognized".format(date_element.tag)
            LOGGER.exception(msg)
            assert False, "{}; XML:\n{}".format(msg, tostring(date_element))

        return dict(ParseChildren(date_element))

# Special Cases

def ParseArticleIdList(element):
    articles = {}

    for article in element.findall("ArticleId"):
        id_type = article.get("IdType")

        if id_type in articles:
            msg = "duplicate {} ArticleId".format(id_type)
            LOGGER.error(msg)
            assert id_type not in articles, \
                "{}; XML:\n{}".format(msg, tostring(element))

        articles[id_type] = article.text

    assert articles, "Empty ArticleIdList; XML:\n{}".format(tostring(element))
    return articles


def ParseMeshHeading(element):
    descriptor = ParseElement(element.find("DescriptorName"))
    qualifiers = [ ParseElement(e) for e in element.findall("QualifierName") ]
    mesh_heading = {"Descriptor": dict([descriptor]) }
    if qualifiers: mesh_heading["Qualifiers"] = dict(qualifiers)
    return mesh_heading


def ParseAbstract(element):
    abstract = {}

    for abstract_text in element.findall("AbstractText"):
        cat = abstract_text.get("NlmCategory", "UNLABELLED").capitalize()

        if cat == "Unlabelled": cat = "AbstractText"
        assert cat not in abstract, \
            "Duplicate AbstractText NlmCategories; XML:\n" \
            "{}".format(tostring(element))
        abstract[cat] = abstract_text.text

    copyright = element.find("CopyrightInformation")
    if copyright is not None: abstract["CopyrightInformation"] = copyright.text
    return abstract