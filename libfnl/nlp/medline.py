"""
.. py:module:: medline
   :synopsis: Download and parse MEDLINE XML records.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>

This module provides functions to fetch and parse NLM PubMed/MEDLINE XML
records.

A simple usage example:

>>> from libfnl.nlp.medline import * # imports only the next two functions
>>> for record in ParseMedlineXml(FetchMedlineXml((11700088, 11748933))):
...     print("PMID", record["_id"], "Title:", record["Article"]["ArticleTitle"])
PMID 11700088 Title: Proton MRI of (13)C distribution by J and chemical shift editing.
PMID 11748933 Title: Is cryopreservation a homogeneous process? Ultrastructure and motility of untreated, prefreezing, and postthawed spermatozoa of Diplodus puntazzo (Cetti).
"""
from http.client import HTTPResponse # function annotation only
from urllib.request import build_opener
from xml.etree.ElementTree import iterparse, tostring
from logging import getLogger
from datetime import date

__all__ = ['FetchMedlineXml', 'ParseMedlineXml']

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

SKIPPED_ELEMENTS = ("OtherID", "OtherAbstract", "SpaceFlightMission",
                    "GeneralNote", "NameID", "ELocationID")
"Ignored tags in MedlineCitation elements that are never parsed."

##############
# DOWNLOADER #
##############

def FetchMedlineXml(pmids:list, timeout:int=60) -> HTTPResponse:
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
    assert len(pmids) < 100, "too many PMIDs"
    url = EUTILS_URL + ','.join(map(str, pmids))
    LOGGER.debug("fetching MEDLINE records from %s", url)
    return URL_OPENER.open(url, timeout=timeout)

##########
# PARSER #
##########

def ParseMedlineXml(xml_stream, pmid_key:str="_id") -> iter([dict]):
    """
    Yield MEDLINE records as dictionaries from an *XML stream*, with the
    **PMID** set as string value of the specified *PMID key* (default:
    **_id**).

    Medline XML records are parsed to dictionaries with the following
    properties:

    * A record is a dictionary built just like a tree, where keys are the tag
      names of the XML record, and values are either dictionaries or lists for
      branches, or the PCDATA strings for leafs in the tree.
    * Each key points to another dictionary if it is a branch. The names of the
      keys are the exact MEDLINE XML tags, except for the special cases
      described below.
    * Keys (XML tags) that end in **List** contain lists, not dictionaries,
      with the tag-list the XML encloses. For example, **AuthorList** contains a
      list of **Author** dictionaries.
    * Leafs where the tag also has attributes are returned as dictionaries,
      putting the actual PCDATA into a key with the name of the tag (again),
      and using the attribute names as additional keys holding the attribute
      values. For example, the (leaf) tag **PMID** sometimes has a **Version**
      attribute, resulting in a value for the dictionary record's top-level
      **PMID** key of either the PMID string itself or a dictionary consisting
      of two entries: **PMID** with the PMID string and **Version** with the
      version string.
    * Otherwise, a (leaf) key contains a string, namely the PCDATA value it
      holds.
    * The PMID of the record is always stored in a key **_id** (or any other
      key specified by *pmid_key*) to ensure equal access to the PMID no
      matter if the **Version** attribute is used.
    * Dates, where possible, are parsed to Python `datetime.date` values,
      unless the tag's values are malformed, whence they are represented as
      dictionaries just like all other XML content. A valid date must have at
      least uniquely and unambiguously identifiable year and month values,
      otherwise the default dictionary tree structure approach is used. In
      general, dates are recognized because their tag names (and hence, the keys
      in the resulting dictionary) all either start or end with the string
      **Date**.
      The only exception is the content of the **MedlineDate** tag, which is
      always a "free-form string" (and hence a malformed date) that neither can
      be parsed to a `datetime.date` value nor a can be represented as
      dictionary.

    Special cases for **Abstract** and **MeshHeadingList**, and for the
    **ArticleIdList** stored under the renamed key **ArticleIds**:

    * The MEDLINE Citation DTD declares that **Abstract** elements contain one
      or more **AbstractText** elements and an optional **CopyrightNotice**
      element. Therefore, the key **Abstract** contains a dictionary with the
      following possible keys: (1) **AbstractText** for all AbstractText
      elements that have no NlmCategory attribute or where that attribute's
      value is "UNLABELLED". (2) A **CopyrightNotice** key if present. (3) For
      all **AbstractText** elements where the NlmCategory attribute is given
      and its value is not "UNLABELLED", the capitalized version of the
      attribute value is used, resulting in the following five additional keys
      that might be found in an **Abstract** dictionary: **Background**,
      **Objective**, **Methods**, **Results**, and **Conclusions**.
    * The (MeSH and XML) tags DescriptorName and QualifierName in the
      **MeshHeadingList** are stored as a list of dictionaries containing a
      **Descriptor** and an (optional) **Qualifiers** key each, each in turn
      holding another dictionary: The names of the MeSH terms as keys and
      `bool`s as values, the latter indicating if a term is tagged major or not.
      In other words, this `bool` represents the value of the MajorTopicYN
      attribute found on DescriptorName and QualifierName elements.
    * The **ArticleId** elements in the ArticleIdList element are stored in the
      key **ArticleIds** as a dictionary (to not confuse default approaches for
      lists described above). The keys of this dictionary are the IdType
      attribute values of **ArticleId** elements, the values the actual PCDATA
      (strings) of the elements (ie., the actual IDs). Therefore, examples of
      keys found in the **ArticleIds** dictionary are **pubmed**, **pmc**, or
      **doi**.

    The NLM MEDLINE Citation DTD itself is found here:
    http://www.nlm.nih.gov/databases/dtd/nlmmedlinecitationset_110101.dtd

    The ArticleIdList is defined in the NLM PubMed Article DTD found here:
    http://www.ncbi.nlm.nih.gov/entrez/query/static/PubMed.dtd
    or
    http://www.ncbi.nlm.nih.gov/corehtml/query/DTD/pubmed_100101.dtd
    """
    for unused_event, element in iterparse(xml_stream):
        if element.tag == "PubmedArticle":
            record = ParseElement(element.find("MedlineCitation"))
            article_id_list = element.find("PubmedData/ArticleIdList")

            if article_id_list is not None:
                record["ArticleIds"] = ParseArticleIdList(article_id_list)

            assert "PMID" in record, \
                "No PMID in:\n{}".format(tostring(element))

            if isinstance(record["PMID"], str):
                record[pmid_key] = record["PMID"]
            else:
                record[pmid_key] = record["PMID"]["PMID"]

            yield record


# Main Element Parser and Regular Elements

def ParseElement(element):
    tag = element.tag

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
    assert content, "Empty element:\n{}".format(tostring(element))
    return content

def ParseChildren(parent):
    known_tags = []
    for child in parent.getchildren():
        if child.tag in SKIPPED_ELEMENTS: continue
        if child.tag == "ArticleDate":
            # Multiple article dates can exist; to avoid overwriting any,
            # use the DateType attribute as prefix of the tag/key.
            tag = "%s%s" % (child.get("DateType", "Electronic"), child.tag)
        else:
            tag = child.tag
        assert tag not in known_tags, \
            "Duplicate child element {}:\n{}".format(tag, tostring(parent))
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
            LOGGER.exception("ParseDateElement: %s not recognized; XML:\n%s",
                             date_element.tag, tostring(date_element))

        return dict(ParseChildren(date_element))


# Special Cases

def ParseArticleIdList(element):
    articles = {}

    for article in element.findall("ArticleId"):
        id_type = article.get("IdType")
        assert id_type not in articles, \
            "Duplicate {} ArticleId:\n{}".format(id_type, tostring(element))
        articles[id_type] = article.text

    assert articles, "Empty ArticleIdList:\n{}".format(tostring(element))
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
            "Duplicate AbstractText NlmCategories:\n{}".format(tostring(element))
        abstract[cat] = abstract_text.text

    copyright = element.find("CopyrightInformation")
    if copyright is not None: abstract["CopyrightInformation"] = copyright.text
    return abstract