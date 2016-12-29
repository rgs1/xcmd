# -*- coding: utf-8 -*-

""" test xcmd proper """

import os
import shutil
import tempfile
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
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_basic(self):
        class Shell(XCmd):
            CONF_PATH = os.path.join(self.temp_dir, '.xcmd')

            @ensure_params(Required('path'))
            def do_cat(self, params):
                self.show_output('cat called with %s' % params.path)

        output = StringIO()
        shell = Shell(setup_readline=False, output_io=output)

        regular = ['cat', 'conf', 'help', 'history', 'pipe']
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
            CONF_PATH = os.path.join(self.temp_dir, '.xcmd')

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

    def test_config(self):
        class Shell(XCmd):
            CONF_PATH = os.path.join(self.temp_dir, '.xcmd')

            def prompt_yes_no(self, _):
                return True

        output = StringIO()
        shell = Shell(setup_readline=False, output_io=output)
        shell.onecmd('conf get')
        shell.onecmd('conf set xcmd_history_size 200')
        shell.onecmd('conf save')
        shell.onecmd('conf get')

        expected = """xcmd_history_size: 100
Configuration saved
xcmd_history_size: 200
"""
        self.assertEqual(expected, output.getvalue())

    def test_history(self):
        class Shell(XCmd):
            CONF_PATH = os.path.join(self.temp_dir, '.xcmd')

            # readline is disable during tests (stdout is not a tty), so we
            # manually track it.
            _history_test = []

            @property
            def history(self):
                return self._history_test

            @ensure_params(Required('path'))
            def do_cat(self, params):
                self._history_test.append('cat %s' % params.path)

            @ensure_params(Required('path'))
            def do_ls(self, params):
                self._history_test.append('ls %s' % params.path)

        output = StringIO()
        shell = Shell(setup_readline=False, output_io=output)
        shell.onecmd('cat /foo')
        shell.onecmd('ls /bar')
        shell.onecmd('history')

        expected = 'cat /foo\nls /bar\n'

        self.assertEqual(expected, output.getvalue())
