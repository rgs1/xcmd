# -*- coding: utf-8 -*-

""" test xcmd proper """

import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from xcmd.xcmd import (
    ensure_params,
    Optional,
    Required,
    XCmd
)


class XCmdTestCase(unittest.TestCase):
    """ Xcmd tests cases """

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_basic(self):
        class Shell(XCmd):
            @ensure_params(Required('path'))
            def do_cat(self, params):
                self.show_output('cat called with %s' % params.path)

        output = StringIO()
        shell = Shell(setup_readline=False, output_io=output)

        regular = ['cat', 'help', 'pipe']
        special = ['!!', '$?']
        self.assertEquals(regular, sorted(shell.commands))
        self.assertEquals(special, sorted(shell.special_commands))
        self.assertEquals(special + regular, sorted(shell.all_commands))

        shell.do_cat('/etc/passwd')
        self.assertEqual('cat called with /etc/passwd\n', output.getvalue())

        # test resolving paths
        self.assertEquals(shell.resolve_path(''), '/')
        self.assertEquals(shell.resolve_path('.'), '/')
        self.assertEquals(shell.resolve_path('..'), '/')
        self.assertEquals(shell.resolve_path('foo'), '/foo')

    def test_pipe(self):
        class Shell(XCmd):
            @ensure_params(Optional('path'))
            def do_ls(self, params):
                self.show_output('/aaa\n/bbb')

            @ensure_params(Required('line'))
            def do_upper(self, params):
                self.show_output(params.line.upper())

        output = StringIO()
        shell = Shell(setup_readline=False, output_io=output)
        shell.do_pipe('ls upper')
        self.assertEqual('/AAA\n/BBB\n', output.getvalue())
