# -*- coding: utf-8 -*-

""" parameters parsing & handling test cases """

import unittest

from xcmd.util import matches


class UtilTestCase(unittest.TestCase):
    """ util tests cases """

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_matches(self):
        commands = ['ls', 'cat', 'catz']
        results = list(matches(commands, 'ca', 0.85))
        self.assertEquals(len(results), 2)
        self.assertIn('cat', results)
        self.assertIn('catz', results)
