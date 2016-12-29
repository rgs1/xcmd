# -*- coding: utf-8 -*-

""" parameters parsing & handling test cases """

from functools import partial

import unittest

from xcmd.complete import (
    complete,
    complete_boolean,
    complete_labeled_boolean,
    complete_values
)


class UtilTestCase(unittest.TestCase):
    """ util tests cases """

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_complete(self):
        completers = [partial(complete_values, ['/foo'])]
        results = complete(completers, '/fo', 'ls /fo')
        self.assertEquals(results, ['/foo'])

    def test_complete_boolean(self):
        completers = [complete_boolean]
        results = complete(completers, 'tru', 'debug tru')
        self.assertEquals(results, ['true'])

    def test_complete_labeled_boolean(self):
        completers = [complete_labeled_boolean('verbose')]
        results = complete(completers, 'verbose=f', 'debug verbose=f')
        self.assertEquals(results, ['verbose=false'])
