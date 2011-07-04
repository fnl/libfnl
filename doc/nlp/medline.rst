##########################################
nlp.medline -- Handling of MEDLINE records
##########################################

.. automodule:: libfnl.nlp.medline

A simple usage example:

>>> from libfnl.nlp.medline import Fetch, Parse
>>> for record in Parse(Fetch((11700088, 11748933))):
...     print("PMID", record["_id"], "Title:", record["Article"]["ArticleTitle"])
PMID 11700088 Title: Proton MRI of (13)C distribution by J and chemical shift editing.
PMID 11748933 Title: Is cryopreservation a homogeneous process? Ultrastructure and motility of untreated, prefreezing, and postthawed spermatozoa of Diplodus puntazzo (Cetti).

Medline XML records are parsed to dictionaries with the following properties:

* A record is a dictionary built just like a tree, where keys are the element names of the XML record, and values are either (1) dictionaries with child elements or (2) lists for branches (**List** attributes), or (3) the PCDATA strings for leafs in the tree.
* Each key points to another dictionary or list if it is not a leaf element. The names of the keys are the exact MEDLINE XML elements, except for a few exceptional special cases described below.
* Keys (XML element names) that end in **List** contain lists, not dictionaries, with the element-list the XML encloses. For example, GrantList will contain a list of Grant dictionaries, but no key explicitly named Grant. Also, as no List has truly relevant attributes, all their attributes (most don't have any) are dropped.
* Leafs (PCDATA elements) where the element also has attributes are returned as dictionaries, putting the actual PCDATA into a key with the name of the dictionary (again), and using the attribute names as additional keys holding the attribute values. For example, the (leaf) element ELocationID has a EIdType attribute, resulting in a key ``ELocationID`` pointing to a dictionary with two keys, ``ELocationID`` (again), now with the actual PCDATA value, and ``EIdType`` with the attribute's value. As this is pretty ugly, in a number of cases this approach is avoided: The **PMID** is always encoded as a tuple of ``(<PMID>, <Version>)`` with Version defaulting to 1, **ISSN**, is encoded as a ``(<IssnType>, <ISSN>)`` tuple, and all leafs that have a single attribute ending with "YN" drop that attribute (except for the important case for MeSH terms, see below), reducing the number of such "Matryoshka-cases" to a bare minimum.
* Otherwise, and in most cases, a leaf simply contains a string, namely the PCDATA value it holds.
* The PMID of the record is always stored in a key **PMID** that is a tuple of the PMID and the Version defaulting to ``1``, no matter if the Version was given or not.
* Dates, where possible, are parsed to Python `datetime.date` values, unless the tag's content is malformed, whence they are represented as dictionaries just like all other XML content. A valid date must have at least uniquely and unambiguously identifiable year and month values, otherwise the default dictionary tree structure approach is used. In general, dates are recognized because their tag names (and hence, the keys in the resulting dictionary) all either start or end with the string **Date**. The only exception is the content of the **MedlineDate** tag, which is always a "free-form string" (and hence always a "malformed" date) that neither can be parsed to a `datetime.date` value nor a can be represented as a dictionary.

Special cases for **Abstract**, **ArticleDate**, **AuthorList** (and **InvestigatorList**), **MeshHeadingList**, and for the **ArticleIdList** stored under the renamed key **ArticleIds**:

* The MEDLINE Citation DTD declares that **Abstract** elements contain one or more **AbstractText** elements and an optional **CopyrightNotice** element. Therefore, the key **Abstract** contains a dictionary with the following possible keys: (1) **AbstractText** for all AbstractText elements that have no ``NlmCategory`` attribute or where that attribute's value is "UNLABELLED". (2) A **CopyrightNotice** key if present. (3) For all **AbstractText** elements where the ``NlmCategory`` attribute is given and its value is not "UNLABELLED", the capitalized version of the attribute value is used, resulting in the following five additional keys that might be found in an **Abstract** dictionary: **Background**, **Objective**, **Methods**, **Results**, and **Conclusions**. However, given that abstracts are usually stored as attachments to the actual record, these keys are transformed to :class:`.text.Unicode` tags in the namespace ``section`` (as "abstract", "background", "objective", ... "copyright"), while the **Abstract** dictionary itself is deleted from text/database documents.
* The **ArticleDate** may be repeated multiple times with different ``DateType`` attributes. To avoid overriding existing article dates, the key ``ArticleDate`` is prefixed with that attribute, which in almost all cases so far is "Electronic", resulting in the key ``ElectronicArticleDate``.
* The **Author** and **Investigator** lists are largely simplified. The ``List`` key points to a list, but the actual Author and Investigator lists are reduced to a single string representing their names. This is in favor over maintaining the highly complex structure found in the XML and makes accessing the names very simple. Also, the redundancy in the names is pruned. For example, MEDLINE would do the following to an author name: ``{`` ``'Initials': "AB",`` ``'ForeName: "A B",`` ``'LastName': "Smith",`` ``'ValidYN': "Y"`` ``}``. This complex representation is reduced to one clear string: ``"A. B. Smith"`` in the list of authors/investigators (note that the ValidYN attribute is ignored, as described above). A check is made if the forename or initials are duplicates. If the forename on the other hand were the expansion of the initials, this expansion is maintained. If the forename's initials do not match with the initials, they are both maintained. For example, initials "A", forename "Charly", and last name "Brown" will concatenate to "A. Charly Brown", while had the initial been "C", the name string would be "Charly Brown" (only).
* The (MeSH) elements ``DescriptorName`` and ``QualifierName`` in the **MeshHeadingList** are stored as a list of tuples containing three items: [0] a Boolean value representing the ``MajorTopicYN`` attribute of the descriptor, [1] the actual ``DescriptorName`` itself, and [2] a (possibly empty) dictionary of qualifiers as ``{ str(QualifierName): bool(MajorTopicYN) }``. In other words, these Booleans indicate if the descriptor or qualifier is major or not (default ``False``) and are the only case where the "YN" attribute is consistently preserved.
* The **ArticleId** elements in the **ArticleIdList** element are stored in the new key **ArticleIds** as a dictionary (to not confuse this key with default approaches for elements ending in ``List`` described above). The keys of this dictionary are the ``IdType`` attribute values of ArticleId elements, the values the actual PCDATA (strings) of the elements (ie., the actual IDs). Therefore, examples of keys found in the ArticleIds dictionary are ``pubmed``, ``pii``, ``pmc``, or ``doi``.

The NLM MEDLINE Citation DTD itself is found here:
http://www.nlm.nih.gov/databases/dtd/nlmmedlinecitationset_110101.dtd

The ArticleIdList is defined in the NLM PubMed Article DTD found here:
http://www.ncbi.nlm.nih.gov/entrez/query/static/PubMed.dtd
or
http://www.ncbi.nlm.nih.gov/corehtml/query/DTD/pubmed_100101.dtd

.. autodata:: libfnl.nlp.medline.EUTILS_URL

.. autodata:: libfnl.nlp.medline.SKIPPED_ELEMENTS

.. autodata:: libfnl.nlp.medline.ABSTRACT_FILE

.. autodata:: libfnl.nlp.medline.FETCH_SIZE

Parse -- Read MEDLINE XML
-------------------------

Yield MEDLINE records as dictionaries from an *XML stream*, with the **PMID** set as string value of the specified *PMID key* (default: **_id**).

.. autofunction:: libfnl.nlp.medline.Parse

Fetch -- Retrieve records via eUtils
------------------------------------

Open an XML stream from the NLM for a list of *PMIDs*, but at most :data:`FETCH_SIZE`
(the approximate upper limit of IDs for this query to the eUtils API).

.. autofunction:: libfnl.nlp.medline.Fetch

Dump - Store records to a Couch DB
----------------------------------

Dump MEDLINE DB records for a given list of *PMIDs* into a Couch *DB*.

Records are treated as :class:`.nlp.text.Binary` data by attaching the title and abstract (if present) to the document. The key **Abstract** in **Article** will be deleted.

Records already existing in a MEDLINE CouchDB can be checked if they are ripe for *update*. This is the case if they are one to ten years old and do not have all three time stamps (created, completed, and revised) or if they are less than one year old and have no a **DateCompleted**.

This "filtered" update mechanism can be overridden and the update can be *force*\ d for all existing records.

.. autofunction:: libfnl.nlp.medline.Dump

Attach -- Additional Binary text records
----------------------------------------

Attach additional files to MEDLINE records as separate records.

The file names must consist of the PMID and the proper file-type extension, eg., ``1234567.html``. The corresponding PMID must exist in the DB. If the article was already attached, it is not replaced. The files are saved as separate documents ID'd by their :attr:`.nlp.text.Binary.hexdigest`.

The created documents are provided with a field ``pmids``, to list the MEDLINE records they map to (as it is possible for the same PMID to have several articles, and vice versa). A DB map view then should be installed to find the reverse mapping::

    { "map":
        "function(rec) {
            if (rec.pmids) {
                for (var i in rec.pmids) {
                    emit(rec.pmids[i])
                }
            }
        }"
    }

The extraction is handled by :func:`.nlp.extract.Extract` and therefore file formats must conform to one of the formats this function can handle and be distinguishable by the file's extension.

.. autofunction:: libfnl.nlp.medline.Attach


