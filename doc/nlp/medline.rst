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

* A record is a dictionary built just like a tree, where keys are the tag names of the XML record, and values are either dictionaries or lists for branches, or the PCDATA strings for leafs in the tree.
* Each key points to another dictionary if it is a branch. The names of the keys are the exact MEDLINE XML tags, except for the special cases described below.
* Keys (XML tags) that end in **List** contain lists, not dictionaries, with the tag-list the XML encloses. For example, **AuthorList** contains a list of **Author** dictionaries.
* Leafs where the tag also has attributes are returned as dictionaries, putting the actual PCDATA into a key with the name of the tag (again), and using the attribute names as additional keys holding the attribute values. For example, the (leaf) tag **PMID** sometimes has a **Version** attribute, resulting in a value for the dictionary record's top-level **PMID** key of either the PMID string itself or a dictionary consisting of two entries: **PMID** with the PMID string and **Version** with the version string.
* Otherwise, a (leaf) key contains a string, namely the PCDATA value it holds.
* The PMID of the record is always stored in a key **_id** (or any other key specified by *pmid_key*) to ensure equal access to the PMID no matter if the **Version** attribute is used.
* Dates, where possible, are parsed to Python `datetime.date` values, unless the tag's content is malformed, whence they are represented as dictionaries just like all other XML content. A valid date must have at least uniquely and unambiguously identifiable year and month values, otherwise the default dictionary tree structure approach is used. In general, dates are recognized because their tag names (and hence, the keys in the resulting dictionary) all either start or end with the string **Date**. The only exception is the content of the **MedlineDate** tag, which is always a "free-form string" (and hence a malformed date) that neither can be parsed to a `datetime.date` value nor a can be represented as a
  dictionary.

Special cases for **Abstract**, **ArticleDate**, **MeshHeadingList**, and for the **ArticleIdList** stored under the renamed key **ArticleIds**:

* The MEDLINE Citation DTD declares that **Abstract** elements contain one or more **AbstractText** elements and an optional **CopyrightNotice** element. Therefore, the key **Abstract** contains a dictionary with the following possible keys: (1) **AbstractText** for all AbstractText elements that have no NlmCategory attribute or where that attribute's value is "UNLABELLED". (2) A **CopyrightNotice** key if present. (3) For all **AbstractText** elements where the NlmCategory attribute is given and its value is not "UNLABELLED", the capitalized version of the attribute value is used, resulting in the following five additional keys that might be found in an **Abstract** dictionary: **Background**, **Objective**, **Methods**, **Results**, and **Conclusions**. However, given that abstracts are usually stored as attachments to the actual record, these keys are found as :class:`.text.Binary` annotations tags in the namespace ``section``, while the **Abstract** dictionary itself is deleted from the records.
* The **ArticleDate** may be repeated multiple times with different *DateType* attributes. To avoid overriding existing article dates, the key **ArticleDate** is prefixed with that attribute, which in almost all cases so far is "Electronic", resulting in the key **ElectronicArticleDate**.
* The (MeSH and XML) tags DescriptorName and QualifierName in the **MeshHeadingList** are stored as a list of dictionaries containing a **Descriptor** and an (optional) **Qualifiers** key each, each in turn holding another dictionary: The names of the MeSH terms as keys and `bool`s as values, the latter indicating if a term is tagged major or not. In other words, this `bool` represents the value of the MajorTopicYN attribute found on DescriptorName and QualifierName elements.
* The **ArticleId** elements in the ArticleIdList element are stored in the key **ArticleIds** as a dictionary (to not confuse default approaches for lists described above). The keys of this dictionary are the IdType attribute values of **ArticleId** elements, the values the actual PCDATA (strings) of the elements (ie., the actual IDs). Therefore, examples of keys found in the **ArticleIds** dictionary are **pubmed**, **pmc**, or **doi**.

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


