""" An augmented version of cmd """

from __future__ import print_function

from distutils.util import strtobool
from functools import partial, wraps

import argparse
import cmd
import os
import shlex
import sys

if not sys.stdout.isatty():
    HAVE_READLINE = False
else:
    try:
        import readline
        HAVE_READLINE = True
    except ImportError:
        HAVE_READLINE = False

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    raw_input
except NameError:
    raw_input = input

from .complete import complete, complete_values
from .conf import Conf, ConfVar
from .conf_store import ConfStore
from .util import matches


PYTHON3 = sys.version_info > (3, )


class BasicParam(object):
    """ a labeled param """
    def __init__(self, label):
        self.label = label

    @property
    def pretty_label(self):
        """ the label as it should be displayed in messages """
        return self.label


class Required(BasicParam):
    """ a required param """
    pass


class IntegerRequired(BasicParam):
    """ a required int param """
    pass


class FloatRequired(BasicParam):
    """ a required int param """
    pass


class Optional(BasicParam):
    """ an optional param """
    def __init__(self, label, default=""):
        super(Optional, self).__init__(label)
        self.default = default

    @property
    def pretty_label(self):
        return '<%s>' % (self.label)


class Multi(BasicParam):
    """ a multi param """
    pass


class MultiOptional(BasicParam):
    """ a (optionally present) multi param """
    pass


class IntegerOptional(BasicParam):
    """ an optional integer param """
    def __init__(self, label, default=0):
        super(IntegerOptional, self).__init__(label)
        self.default = default


class BooleanOptional(BasicParam):
    """ an optional boolean param """
    def __init__(self, label, default=False):
        super(BooleanOptional, self).__init__(label)
        self.default = default


class BooleanAction(argparse.Action):
    """ used to parse boolean string params """
    def __call__(self, parser, namespace, values, option_string=None):
        value = values if isinstance(values, bool) else values.lower() == 'true'
        setattr(namespace, self.dest, value)


class LabeledBooleanOptional(BooleanOptional):
    """ like a BooleanOption, but can be labeled (i.e.: recurse=true) """
    pass


class LabeledBooleanAction(argparse.Action):
    """ used to parse (potentially) labeled boolean string params (i.e.: recurse=true) """
    def __call__(self, parser, namespace, values, option_string=None):
        if isinstance(values, bool):
            value = values
        else:
            if '=' in values:
                _, values = values.rsplit('=', 1)
            value = values.lower() == 'true'
        setattr(namespace, self.dest, value)


class ShellParser(argparse.ArgumentParser):
    """ a cmdline parser useful for implementing shells """

    class ParserException(Exception):
        """ parser generated exception """
        pass

    @classmethod
    def from_params(cls, params):
        """ generate an instance from a list of params """
        parser = cls()
        for param in params:
            if isinstance(param, Required):
                parser.add_argument(param.label)
            elif isinstance(param, IntegerRequired):
                parser.add_argument(param.label, type=int)
            elif isinstance(param, FloatRequired):
                parser.add_argument(param.label, type=float)
            elif isinstance(param, Optional):
                parser.add_argument(param.label, nargs='?', default=param.default, type=str)
            # LabeledBooleanOptional is also a BooleanOptional, so try to match it first
            elif isinstance(param, LabeledBooleanOptional):
                parser.add_argument(
                    param.label, nargs='?', default=param.default, action=LabeledBooleanAction)
            elif isinstance(param, BooleanOptional):
                parser.add_argument(param.label, nargs='?', default=param.default, action=BooleanAction)
            elif isinstance(param, IntegerOptional):
                parser.add_argument(param.label, nargs='?', default=param.default, type=int)
            elif isinstance(param, Multi):
                parser.add_argument(param.label, nargs='+')
            elif isinstance(param, MultiOptional):
                parser.add_argument(param.label, nargs='*')
            else:
                raise ValueError('Unknown parameter type: %s' % (param))
        parser.set_valid_params(' '.join(param.pretty_label for param in params))
        return parser

    @property
    def valid_params(self):
        """ a string with the valid params for this parser instance """
        return self.__dict__['_valid_params']

    def set_valid_params(self, params):
        """ sets the string list of valid params """
        self.__dict__['_valid_params'] = params

    def error(self, message):
        """ handle an error raised by ArgumentParser """
        full_msg = 'Wrong params: %s, expected: %s' % (message, self.valid_params)
        raise self.ParserException(full_msg)

    def print_help(self, *args, **kwargs):
        """ keep it quiet """
        pass

    def exit(self, *args, **kwargs):
        """ parsers never quit """
        pass


def interruptible(func):
    """ handle KeyboardInterrupt for func """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
    return wrapper


def ensure_params_with_parser(parser, func):
    """ parse args with parser and run func """
    @wraps(func)
    def wrapper(*args):
        try:
            params = parser.parse_args(shlex.split(args[1]))
            return func(args[0], params)
        except (ShellParser.ParserException, ValueError) as ex:
            doc = getattr(func, '__doc__', None)
            command = func.__name__.replace('do_', '')
            print_func = getattr(wrapper, 'print_function', None)
            if callable(print_func):
                print_func('\n%s\n\n%s: %s' % (ex, command, doc) if doc else ex)
            else:
                print('\n%s\n\n%s: %s' % (ex, command, doc) if doc else ex)

    return wrapper


def ensure_params(*params):
    """ decorates with a Parser built from params """
    parser = ShellParser.from_params(params)
    return partial(ensure_params_with_parser, parser)


MAX_OUTPUT = 1 << 20


class XCmd(cmd.Cmd):
    """ extends cmd.Cmd """

    CONF_PATH = os.path.join(os.environ['HOME'], '.xcmd')
    DEFAULT_CONF = Conf(
        ConfVar(
            'xcmd_history_size',
            'Number of commands to save into history',
            100
        )
    )

    def __init__(self, hist_file_name=None, setup_readline=True, output_io=sys.stdout):
        cmd.Cmd.__init__(self)

        self.curdir = '/'
        self.olddir = '/'

        self._output = output_io
        self._last_output = ''

        # config management
        self._conf_store = ConfStore(path=self.CONF_PATH)
        self._conf_store.ensure_path()
        self._conf = self._conf_store.get('config')
        if self._conf is None:
            self._conf_store.save('config', self.DEFAULT_CONF)
            self._conf = self._conf_store.get('config')

        if setup_readline:
            if hist_file_name is None:
                # default
                hist_file_name = self._conf_store.full_path('history')
            self._setup_readline(hist_file_name)

        # build the list of regular commands
        self._regular_commands = [name[3:] for name in self.get_names() if name[:3] == 'do_']

        # special commands dispatch map
        self._special_commands = {
            '!!': self.run_last_command,
            '$?': self.echo_last_output,
        }

    @property
    def output(self):
        """ the io output object """
        return self._output

    def output_context(self):
        """ context manager to redirect output to a string io """
        class OutputContext(object):
            def __init__(self, xcmd):
                self._xcmd = xcmd
                self._orig_output = None
                self._buf = StringIO()

            @property
            def value(self):
                return self._buf.getvalue()

            def reset(self):
                self._buf.seek(0)
                self._buf.truncate()

            def __enter__(self):
                # TODO: take xcmd.output_lock
                self._orig_output = self._xcmd._output
                self._xcmd._output = self._buf
                return self

            def __exit__(self, type, value, traceback):
                # TODO: release xcmd.output_lock
                self._xcmd._output = self._orig_output

        return OutputContext(self)

    @ensure_params(Multi('cmds'))
    def do_pipe(self, params):
        """
        Pipe a series of commands

        pipe <cmd1> <cmd2> ... <cmdN>

        Calls <cmdN> for each output line of <cmdN-1>.

        Example:

        > ls /foo
        a
        b
        > get /foo/a
        a content
        > get /foo/b
        b content

        > cd /foo
        > pipe ls get
        a content
        b content

        """
        if len(params.cmds) < 2:
            raise ValueError('At least two commands are needed.')

        rv = True
        output = ''
        with self.output_context() as octxt:
            for command in params.cmds:
                inlines = output.rstrip('\n').split('\n')
                output = ''
                for line in inlines:
                    rv = self.onecmd('%s %s' % (command, line))
                    if rv is False:
                        # just output the error
                        output = octxt.value
                        break
                    output += octxt.value
                    octxt.reset()

        self.show_output(output.rstrip('\n'))
        return rv

    def show_output(self, fmt_str, *params, **kwargs):
        """ MAX_OUTPUT chars of the last output is available via $? """
        if PYTHON3:
            fmt_str = str(fmt_str)

        out = fmt_str % params if len(params) > 0 else fmt_str

        if out is not None:
            self._last_output = out if len(out) < MAX_OUTPUT else out[:MAX_OUTPUT]

        if not PYTHON3 and not sys.stdout.isatty() and out:
            out = out.encode('utf-8')

        end = kwargs['end'] if 'end' in kwargs else '\n'

        print(out, file=self._output, end=end)

    def prompt_yes_no(self, question):
        """ yes or no question """
        while True:
            self.show_output('%s [y/n]: ', question, end='')
            try:
                return strtobool(raw_input().lower())
            except ValueError:
                self.show_output('Please respond with \'y\' or \'n\'.')

    @property
    def commands(self):
        """ available commands, not including the special ones """
        return self._regular_commands

    @property
    def special_commands(self):
        """ special, builtin, commands """
        cmds = self._special_commands.keys()
        return list(cmds) if PYTHON3 else cmds

    @property
    def all_commands(self):
        """ regular + special commands """
        return self.commands + self.special_commands

    def default(self, line):
        try:
            args = shlex.split(line)
        except ValueError:
            if not line.startswith("#"):
                self.show_output("No closing quotation")
            return False

        if len(args) > 0 and not args[0].startswith('#'):  # ignore commented lines, ala Bash
            command = self._special_commands.get(args[0])
            if command:
                return command(args[1:])
            else:
                similar = list(matches(self.all_commands, args[0], 0.85))
                if len(similar) == 1:
                    self.show_output('Unknown command, maybe you meant: %s', similar[0])
                elif len(similar) > 1:
                    options = ', '.join(similar[:-1])
                    options += ' or %s' % (similar[-1])
                    self.show_output('Unknown command, maybe you meant: %s', options)
                else:
                    self.show_output('Unknown command: %s', args[0])

        return False

    def run_last_command(self, *_):
        self.onecmd(self.last_command)

    def echo_last_output(self, *_):
        print(self._last_output, file=self._output)

    def emptyline(self):
        pass

    def run(self, intro=None):
        """ runs xcmd's main loop """
        self.intro = intro
        self.cmdloop()

    def _exit(self, newline=True):
        """ gets called before exiting """
        if newline:
            self.show_output('')
        sys.exit(0)

    def resolve_path(self, path):
        """
        transform a given relative or abbrev path into a fully resolved one

        i.e.:
          ''          -> /full/current/dir
          '.'         -> /full/current/dir
          '..'        -> /full/parent/dir
          'some/path' -> /full/some/path
        """
        if path in ['', '.']:
            path = self.curdir
        elif path == '..':
            path = os.path.dirname(self.curdir)
        elif path == '-':
            path = self.olddir
        elif not path.startswith('/'):
            path = os.path.join(self.curdir, path)

        return os.path.normpath(path)

    def update_curdir(self, path):
        """ path is a resolved path """
        self.olddir = self.curdir
        self.curdir = path
        self.prompt = '%s%s> ' % (self.state, path)

    @property
    def state(self):
        """ the state displayed in the prompt """
        return ''

    @property
    def last_command(self):
        """ returns the last executed command """
        if not HAVE_READLINE:
            return ''

        cur_size = readline.get_current_history_length()
        return readline.get_history_item(cur_size - 1)

    @property
    def history(self):
        """ returns all the executed commands """
        if not HAVE_READLINE:
            return

        for i in range(0, readline.get_current_history_length()):
            yield readline.get_history_item(i)

    def _setup_readline(self, path):
        """ configures readline, if it's available """
        if not HAVE_READLINE or path is None:
            return

        try:
            readline.read_history_file(path)
        except IOError:
            pass

        import atexit
        atexit.register(readline.write_history_file, path)

    @ensure_params(Required('cmd'), MultiOptional('args'))
    def do_conf(self, params):
        """
\x1b[1mNAME\x1b[0m
        conf - Runtime configuration management

\x1b[1mSYNOPSIS\x1b[0m
        conf <describe|get|save|set> [args]

\x1b[1mDESCRIPTION\x1b[0m

        conf describe [name]

          describes the configuration variable [name], or all if no name is given.

        conf get [name]

          with a name given, it gets the value for the configuration variable. Otherwise, it'll
          get all available configuration variables.

        conf set <name> <value>

          sets the variable <name> to <value>.

        conf save

          persists the running configuration.

\x1b[1mEXAMPLES\x1b[0m
        > conf get
        foo: bar
        two: dos

        > conf describe foo
        foo is used to set the operating parameter for bar

        > conf get foo
        bar

        > conf set foo 2

        > conf get foo
        2

        > conf save
        Configuration saved.

        """
        conf = self._conf
        error = 'Unknown variable.'

        def get():
            if len(params.args) == 0:
                out = str(conf)
            else:
                out = conf.get_str(params.args[0], error)
            self.show_output(out)

        def setv():
            if len(params.args) != 2:
                raise ValueError
            cvar = conf.get(params.args[0])
            if cvar:
                cvar.value = params.args[1]
            else:
                self.show_output(error)

        def describe():
            if len(params.args) == 0:
                self.show_output(conf.describe_all())
            else:
                self.show_output(conf.describe(params.args[0], error))

        def save():
            if self.prompt_yes_no('Save configuration?'):
                if self._conf_store.save('config', self._conf):
                    self.show_output('Configuration saved')
                # FIXME: not dealing with failure now

        cmds = {
            'get': get,
            'describe': describe,
            'save': save,
            'set': setv,
        }

        cmd = cmds.get(params.cmd)
        if not cmd:
            raise ValueError
        cmd()

    def complete_conf(self, cmd_param_text, full_cmd, *rest):
        complete_cmd = partial(complete_values, ['get', 'describe', 'save', 'set'])
        complete_var = partial(complete_values, self._conf.keys())
        completers = [complete_cmd, complete_var]
        return complete(completers, cmd_param_text, full_cmd, *rest)

    @ensure_params(Optional("match"))
    def do_history(self, params):
        """
\x1b[1mNAME\x1b[0m
        history - Prints all previous commands

\x1b[1mSYNOPSIS\x1b[0m
        history [match]

\x1b[1mOPTIONS\x1b[0m
        * match: only include commands if match is substr (default: '')

\x1b[1mEXAMPLES\x1b[0m
        > history
        ls
        cat /foo

        # only those that match 'cat'
        > history cat
        cat /foo
        cat /bar

        """
        for hcmd in self.history:
            if hcmd is None:
                continue

            if params.match == '' or params.match in hcmd:
                self.show_output('%s', hcmd)

    def complete_history(self, cmd_param_text, full_cmd, *rest):
        completers = [partial(complete_values, self.commands)]
        return complete(completers, cmd_param_text, full_cmd, *rest)
