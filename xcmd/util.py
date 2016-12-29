""" helper methods """

import difflib


def matches(words, query, threshold):
    query_len = float(len(query))
    for word in words:
        s = difflib.SequenceMatcher(None, word, query)
        match = ''.join(word[i:i + n] for i, j, n in s.get_matching_blocks() if n)
        if len(match) / query_len >= threshold:
            yield word
