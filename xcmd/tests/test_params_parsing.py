# -*- coding: utf-8 -*-

""" parameters parsing & handling test cases """

import threading
import unittest

from xcmd.xcmd import (
    ensure_params,
    BooleanOptional,
    FloatRequired,
    IntegerRequired,
    IntegerOptional,
    LabeledBooleanOptional,
    Multi,
    MultiOptional,
    Optional,
    Required
)


class ParamsParsingTestCase(unittest.TestCase):
    """ parameters parsing """

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_required(self):
        called = threading.Event()

        @ensure_params(Required('path'))
        def cat(self, params):
            self.assertEquals(params.path, '/etc/passwd')
            called.set()

        cat(self, '/etc/passwd')
        self.assertTrue(called.is_set())

        # now, try with the required param missing
        called.clear()
        cat(self, '  ')
        self.assertFalse(called.is_set())

    def test_integer_required(self):
        called = threading.Event()

        @ensure_params(IntegerRequired('number'))
        def square_root(self, params):
            self.assertEquals(params.number, 49)
            called.set()

        square_root(self, '49')
        self.assertTrue(called.is_set())

        # now, try without an int
        called.clear()
        square_root(self, 'fortynine')
        self.assertFalse(called.is_set())

    def test_integer_optional(self):
        called = threading.Event()

        @ensure_params(IntegerOptional('number'))
        def square_root(self, params):
            self.assertEquals(params.number, 49)
            called.set()

        square_root(self, '49')
        self.assertTrue(called.is_set())

        # now, try without an optional int
        @ensure_params(IntegerOptional('number'))
        def square_root(self, params):
            self.assertEquals(params.number, 0)
            called.set()

        called.clear()
        square_root(self, ' ')
        self.assertTrue(called.is_set())

    def test_float_required(self):
        called = threading.Event()

        @ensure_params(FloatRequired('number'))
        def absolute_value(self, params):
            self.assertEquals(params.number, -1.0)
            called.set()

        absolute_value(self, '-1.0')
        self.assertTrue(called.is_set())

        # now, try without an int
        called.clear()
        absolute_value(self, 'minus one')
        self.assertFalse(called.is_set())

    def test_optional(self):
        @ensure_params(Optional('path', '-'))
        def cat(self, params):
            self.assertEquals(params.path, '-')

        cat(self, '  ')

    def test_multi(self):
        @ensure_params(Multi('cmds'))
        def cat(self, params):
            self.assertEquals(len(params.cmds), 2)
            self.assertEquals(params.cmds[0], 'foo')
            self.assertEquals(params.cmds[1], 'bar')

        cat(self, 'foo bar')

    def test_multi_optional(self):
        called = threading.Event()

        @ensure_params(MultiOptional('args'))
        def cat(self, params):
            self.assertEquals(len(params.args), 2)
            self.assertEquals(params.args[0], 'foo')
            self.assertEquals(params.args[1], 'bar')
            called.set()

        cat(self, 'foo bar')
        self.assertTrue(called.is_set())

        # without the optional multi args
        @ensure_params(MultiOptional('args'))
        def cat(self, params):
            self.assertEquals(len(params.args), 0)
            called.set()

        called.clear()
        cat(self, ' ')
        self.assertTrue(called.is_set())

    def test_boolean_optional(self):
        called = threading.Event()

        @ensure_params(Required('path'), BooleanOptional('verbose'))
        def delete(self, params):
            self.assertEquals(params.path, '/etc/passwd')
            self.assertEquals(params.verbose, False)
            called.set()

        delete(self, '/etc/passwd ')
        self.assertTrue(called.is_set())

        # set the optional param
        @ensure_params(Required('path'), BooleanOptional('verbose'))
        def delete(self, params):
            self.assertEquals(params.path, '/etc/passwd')
            self.assertEquals(params.verbose, True)
            called.set()

        called.clear()
        delete(self, '/etc/passwd true')
        self.assertTrue(called.is_set())

    def test_labeled_boolean_optional(self):
        called = threading.Event()

        @ensure_params(Required('path'), LabeledBooleanOptional('verbose'))
        def delete(self, params):
            self.assertEquals(params.path, '/etc/passwd')
            self.assertEquals(params.verbose, False)
            called.set()

        delete(self, '/etc/passwd ')
        self.assertTrue(called.is_set())

        # set the optional param
        @ensure_params(Required('path'), LabeledBooleanOptional('verbose'))
        def delete(self, params):
            self.assertEquals(params.path, '/etc/passwd')
            self.assertEquals(params.verbose, True)
            called.set()

        called.clear()
        delete(self, '/etc/passwd verbose=true')
        self.assertTrue(called.is_set())
