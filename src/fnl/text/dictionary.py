"""
.. py:module:: fnl.text.dictionary
   :synopsis: Recognize terms in token streams and tag them with their mapped keys.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from fnl.text.strtok import Tokenizer


class Node(object):
    """
    Nodes in a Dictionary tree point to child Nodes via token-tagged edges
    and possibly have a Leaf that maps to a Dictionary key.
    """

    def __init__(self, *leafs, **edges):
        self.edges = edges
        self.leafs = sorted(leafs)

    def __eq__(self, other):
        if isinstance(other, Node):
            return id(self) == id(other) or (self.leafs == other.leafs and self.edges == other.edges)
        else:
            return False

    def __repr__(self):
        return "Node<leafs={}, edges={}>".format(self.leafs, self.edges)

    def createOrGet(self, token):
        """
        Create or get the Node pointed to by `token` from this node.

        :param token: edge label
        :return: the child :class:`Node` instance
        """
        if token in self.edges:
            node = self.edges[token]
        else:
            node = Node()
            self.edges[token] = node

        return node

    def setLeaf(self, key, order):
        """
        Store the `key` as a leaf of this node at position `order`.

        The key is the main key if there is no leaf yet,
        or if `order` is smaller than all the existing leafs' order values.
        Otherwise, it the key is stored as one of the alternative keys.
        At equal order values, keys are sorted in lexical order.

        :param key: to store
        :param order: value used to sort/compare keys (smaller first)
        """
        self.leafs.append((order, key))
        self.leafs = sorted(self.leafs)

    @property
    def key(self):
        """Return the main key of this leaf."""
        return self.leafs[0][1] if self.leafs else None


class Dictionary(object):
    """
    Dictionaries are trees of token-edges where Nodes at the end of token paths
    that represent a Dictionary term map to the term's key using a Leaf object.
    """

    B = 'B-%s'
    I = 'I-%s'
    O = 'O'

    @staticmethod
    def merge(node1, node2) -> Node:
        """
        Merge two nodes to produce a new, united node with all their children.

        :param node1: to merge
        :param node2: to merge
        :return: a merged node, always a copy
        """
        if node1 == node2:
            return Node(*node1.leafs, **node1.edges)

        edges = node1.edges.copy()

        for e in node2.edges:
            if e in edges:
                edges[e] = Dictionary.merge(edges[e], node2.edges[e])
            else:
                edges[e] = node2.edges[e]

        return Node(*sorted(node1.leafs + node2.leafs), **edges)

    def __init__(self, data: iter, tokenizer: Tokenizer):
        """
        Initialize a new Dictionary using a data iterator and a (term) tokenizer.

        :param data: an iterator over (key, term, *order) tuples
        :param tokenizer: to tokenize terms
        """
        self.root = Node()

        for key, term, *order in data:
            node = self.root

            for start, end, tag, morphology in tokenizer.tag(term):
                # special matching condition: single letter match
                # can use both cases inside an already opened match
                if start > 0 and end - start == 1:
                    node = node.createOrGet(term[start:end].lower())
                else:
                    node = node.createOrGet(term[start:end])

            node.setLeaf(key, order)

    def walk(self, token_stream: iter) -> iter:
        """
        Yield a stream of "B-"/"I-" prefixed keys for each token that matches
        (part of) a term or "O" if no match is found for the current token.

        A matching term starts with "B-[key]", continues with "I-[key]",
        and ends with an "O" (or the stream itself ends).
        That means that per token only the first-best matching term is reported.

        :param token_stream: token strings to match with the dictionary
        :return: BIO-key strings, one per token string
        """
        queue = []
        last = None

        for token in token_stream:
            queue = self._match(queue, token, last)
            yield from self._iterpop(queue)
            last = token

        # close all paths
        for idx in range(len(queue)):
            path = queue[idx]

            if path is not None:
                queue[idx] = tuple(path)

        yield from self._iterpop(queue, True)

    def _iterpop(self, queue, all=False) -> iter:
        """
        Yield tags on the queue that contain values.

        :param queue: to process
        :return: a tag generator
        """
        count = 0 if all else 1
        while len(queue) > count:
            if queue[0] is None:
                queue.pop(0)
                yield Dictionary.O
            elif type(queue[0]) is tuple:
                for tag in self._resolve(queue.pop(0), queue):
                    yield tag
            else:
                break

    @staticmethod
    def _isCapitalizeD(last, token):
        # last="Capitalize" and token="D"
        #return last and len(token) == 1 and last[0].isupper() and token.isupper()
        # alt approach: only require last="whatever" and token="U"
        return last and len(token) == 1 and last.isalpha() and token.isupper()

    def _match(self, queue, token:str, last:str) -> list:
        # the alternative path: join the current token with the last if the current token is
        # a single upper-case letter and the last token is capitalized, to create a token of
        # the form "CapitalizeD", but then upper-casing all letters
        alt = "{}{}".format(last, token).upper() if Dictionary._isCapitalizeD(last, token) else None
        upper = token.upper() if token.islower() else None

        for idx in range(len(queue)):
            if queue[idx] is None or type(queue[idx]) is tuple:
                continue

            path = queue[idx] # the current path that may be extended
            edges = path[-1].edges # all outgoing edges on that path that can be used to extend it
            altNode = path[-2] if alt and len(path) > 1 else self.root # the alternative path

            if token in edges:
                if alt in altNode.edges:
                    path.append(Dictionary.merge(edges[token], altNode.edges[alt]))
                else:
                    path.append(edges[token])
            elif len(token) == 1 and token.isupper() and token.lower() in edges:
                # special matching condition: single letter match
                # with swapped case inside an already opened path
                path.append(edges[token.lower()])
            elif alt in altNode.edges:
                # allow joint token matches if the second token is a single, upper-case letter
                # and the first token was a letter token beginning with upper-case, too
                path.append(altNode.edges[alt])
            elif upper and upper in edges:
                # allow full-token lower-case to upper-case transitions
                # to detect mentions of genes written in all lower-case
                path.append(edges[upper])
            else:
                # "close" this path
                queue[idx] = tuple(path)

        if token in self.root.edges:
            if upper and upper in self.root.edges:
                # "open" a new path 1/3
                queue.append([Dictionary.merge(self.root.edges[token], self.root.edges[upper])])
            else:
                # "open" a new path 2/3
                queue.append([self.root.edges[token]])
        elif upper and upper in self.root.edges:
            # "open" a new path 3/3
            queue.append([self.root.edges[upper]])
        elif alt in self.root.edges:
            # No check of len(queue) required:
            # if this fails, something is wrong with _iterpop,
            # because it should guarantee that at least the last item is left
            q = queue[-1]

            if q is None:
                q = queue[-1] = []
            elif type(q) == tuple:
                q = queue[-1] = list(q)

            q.append(self.root.edges[alt])
            q.append(self.root.edges[alt])
            queue.append(None)
        else:
            queue.append(None)

        return queue

    def _resolve(self, path, queue) -> iter:
        for node in reversed(path):
            if node.key:
                idx = 0
                ikey = Dictionary.I % node.key
                yield Dictionary.B % node.key

                while path[idx] != node:
                    yield ikey
                    idx += 1
                    # overlapping terms are dropped
                    queue.pop(0)

                return

        # the path did not contain a key
        yield Dictionary.O