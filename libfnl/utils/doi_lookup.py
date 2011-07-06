"""
.. py:module:: doi_lookup
   :synopsis: Search for a DOI on crossref.org using metadata.

.. moduleauthor: Florian Leitner <florian.leitner@gmail.com>

Search for a DOI on crossref.org using article/book metadata.
"""
from logging import getLogger
from urllib.parse import urlencode, unquote_plus
from urllib.request import urlopen

LOGGER = getLogger('doi_lookup')

def lookup(credentials:str, **keys:{str: str}) -> {str, str}:
    """
    Lookup DOI of articles in journals or conference proceedings, as well
    as the DOIs for books.

    You need to request an account to use CrossRef_ for the lookups. The
    *credentials* usually will be the email by which you registered, or a
    ``<username>:<password>`` string.

    Minimally required fields are ``author`` and/or ``page`` as well as
    ``issn``/``isbn`` and/or ``title``/``vol_title``, and non-empty.

    To query for **Journal/Proceeding** DOIs, at least one of these *keys* is
    required:

    * ``issn``: Journal or conference proceedings ISSN.
    * ``title``: Journal title or abbreviation.

    For **Book/Proceeding** queries, at least ``isbn`` or ``vol_title`` is
    required:

    * ``isbn``: Book ISBN or conference proceedings ISSN (req.).
    * ``vol_title``: The book title (req.).
    * ``ser_title``: The serial title.
    * ``component_number``: Chapter, section or part (e.g. 'Section 3').

    Common *keys* for any lookup, at least ``author`` or ``page`` is required:

    * ``author``: First Author or Editor surname.
    * ``page``: First page.
    * ``volume``: Volume.
    * ``issue``: Edition number (e.g. 3).
    * ``year``: Year published.
    * ``resource_type``: 'full_text', 'abstract_only' or 'bibliographic_record'
    * ``key``: To track queries.
    * ``doi``: The DOI (non-empty in the returned dictionary if the query was
      successful).

    :return: A dictionary of *keys*, but with the ``doi`` non-empty if found.
    :raise ValueError: If the minimally required fields are not set or a key's
        value contains the pipe character (``|``).
    .. _CrossRef: http://www.crossref.org/requestaccount/
    """
    # Example query:
    # http://doi.crossref.org/servlet/query?pid=XXX:YYY&format=piped&qdata=
    # 08888809|Mol.+Endocrinol.|Wang|13|8||1999|||
    LOGGER.debug('query: %s', ', '.join(
        '{}="{}"'.format(*i) for i in keys.items()
    ))
    check = lambda *fields: any(f in keys for f in fields)

    if not all('|' not in val for val in keys.values()):
        raise ValueError('pipe chars not allowed in key value')

    if not check('author', 'page'):
        raise ValueError('required author/page field missing')

    if check('issn', 'title'):
        fields = ('issn', 'title', 'author', 'volume', 'issue', 'page', 'year',
                  'resource_type', 'key', 'doi')
        piped = '{issn}|{title}|{author}|{volume}|{issue}|{page}|{year}|'\
                '{resource_type}|{key}|{doi}'
    elif check('isbn', 'vol_title'):
        fields = ('isbn', 'ser_title', 'vol_title', 'author', 'volume',
                  'issue', 'page', 'year', 'component_number', 'resource_type',
                  'key', 'doi')
        piped = '{isbn}|{ser_title}|{vol_title}|{author}|{volume}|'\
                '{issue}|{page}|{year}|{component_number}|{resource_type}|'\
                '{key}|{doi}'
    else:
        raise ValueError('required issn/title or isbn/vol_title field missing')

    for f in fields:
        if f not in keys: keys[f] = ''

    piped = piped.format(keys)
    params = {'pid': credentials, 'format': 'piped', 'qdata': piped}
    url = "http://doi.crossref.org/servlet/query?{}".format(urlencode(params))
    response = urlopen(url)
    result = response.read()
    return dict(zip(fields, unquote_plus(result).split('|')))