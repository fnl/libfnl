# coding=utf-8
"""
.. py:module:: fnl.stat.kappa
   :synopsis: Functions to calculate inter-rater agreements.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

import logging

def Fleiss(frequency_matrix):
    """
    Compute Fleiss' Kappa (a `float` value) for two or more raters.

    .. seealso::

        `WikiPedia on Fleiss' Kappa <http://en.wikipedia.org/wiki/Fleiss_kappa>`_

    Each row ``s`` in the *frequency matrix* ``M`` represents a subject the
    raters voted on. Each subject row then has a list exactly as long as
    there are rating categories ``c``, holding the number of raters that
    voted for the respective category:

        M\ :sub:`s,c`

    Each rater ``r`` must have voted exactly once on each subject. So these
    sum of each row ``s`` in the matrix must be the same and equal to the
    total number of raters ``R``:

        ∀s: ∑M\ :sub:`s` = R

    And the value each column ``c`` must be in the range [0..R]:

        ∀s,c: 0 ≤ M\ :sub:`s,c` ≤ R

    :param frequency_matrix: A matrix of subjects × categories.
    :raises AssertionError, IndexError: If any row in the *frequency matrix*
                                        has a different `sum` or `len` than
                                        the first.
    """
    M = frequency_matrix
    R = FindAndCheckRaters(M)
    S = len(M)
    C = len(M[0])

    # Compute proportion of votes per category: p_c
    p = [0.0] * C
    SR = S * R

    for c in range(C):
        for s in range(S):
            p[c] += M[s][c]
        
        p[c] /= SR

    # Compute rater agreement per subject: P_s
    P = [0.0] * S
    R2ub = R * (R - 1)

    for s in range(S):
        for c in range(C):
            P[s] += M[s][c] * M[s][c]

        #noinspection PyUnresolvedReferences
        P[s] = (P[s] - R) / R2ub

    # Compute the mean [agreement] of the P_s's
    mean_agreement = sum(P) / S

    # Compute the MSE of the proportion of votes
    var_votes = sum(p_c * p_c for p_c in p)

    # Return Fleiss' Kappa
    return (mean_agreement - var_votes) / (1 - var_votes)

def CreateRatingMatrix(ratings:[{str: str}]) -> [[int]]:
    """
    :param ratings: A list of {subject: vote} dictionaries; one per rater.
    :return list: A rating frequency matrix as required for the Kappa
                  functions.
    """
    # Determine subjects
    assert len(ratings) > 1, "at least two raters' results required"
    subjects = set(ratings[0].keys())
    for r in ratings:
        test = set(r.keys())
        assert test == subjects, \
            "non-equal subject IDs in rating files:\n{}\n{}".format(
                (test - subjects), (subjects - test)
            )
    subjects = sorted(subjects)
    logging.debug("Subjects: %s", subjects)
    logging.info("Total: %s subjects", len(subjects))

    # Determine categories
    categories = set()
    for r in ratings: categories.update(r.values())
    categories = sorted(categories)
    logging.info("Categories: %s", categories)

    # Create and return rating frequency matrix
    #noinspection PyUnusedLocal
    M = [[0] * len(categories) for i in range(len(subjects))]

    for r in ratings:
        for i, s in enumerate(subjects):
            j = categories.index(r[s])
            M[i][j] += 1

    return M

def FindAndCheckRaters(M:[[int]]) -> int:
    """
    Find the number of raters ``R`` and assert that the sum of each row has
    that same number.

    :raises AssertionError: If any row contains a different sum of raters or
                            a different number of categories (ie. length).
    """
    R, C = sum(M[0]), len(M[0])
    assert all(sum(s) == R and len(s) == C for s in M), \
        "non-equal number of raters or categories in matrix"
    return R

