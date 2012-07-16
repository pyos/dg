import os
import sys
import runpy
import builtins

from .. import parse
from .. import compile


class Interactive:

    def __init__(self, input=sys.stdin):

        super().__init__()

        self.input    = input
        self.parser   = parse.r()
        self.compiler = compile.r()

    # Read the remaining input, compile it, run, then exit.
    #
    # :param ns: the global namespace.
    #
    # :return: does not return.
    #
    def run(self, ns):

        p = self.parser.reset(self.input.read(), self.input.name)
        c = self.compiler.compile(next(p), name='<module>')
        eval(c, ns)
        exit(0)

    # Compile and run a single command.
    #
    # :param code: whatever was read so far.
    #
    # :param ns: the global namespace.
    #
    # :return: whether the input was complete.
    #
    def command(self, code, ns):

        p = self.parser.compile_command(code)
        c = self.compiler.compile(p, name='<module>') if p is not None else p
        c and sys.displayhook(eval(c, ns))
        return c

    # Preprocess the traceback given its root frame.
    #
    # :param trace: `Exception.__traceback__`
    #
    # :return: a new traceback.
    #
    def traceback(self, trace):

        uses_runpy = False

        internal    = {self.shell.__code__, self.command.__code__, self.run.__code__}
        runpy_stuff = {runpy._run_module_as_main.__code__, runpy._run_code.__code__}

        # Skip over all entries in `runpy` module.
        while trace and trace.tb_frame.f_code in runpy_stuff:

            trace = trace.tb_next
            uses_runpy = True

        # If `runpy` was used, the next line is in `__main__`.
        trace = trace and trace.tb_next if uses_runpy else trace

        # If the next lines are in this module, skip them, too.
        while trace and trace.tb_frame.f_code in internal:

            trace = trace.tb_next

        return trace

    # Start an interactive shell.
    #
    # :param name: name of the module.
    #
    # :return: runs indefinitely.
    #
    def shell(self, name='__main__'):

        environ = {'__name__': name, '__builtins__': __builtins__}

        self.input.isatty() or self.run(environ)

        sys.ps1 = getattr(sys, 'ps1', '>>> ')
        sys.ps2 = getattr(sys, 'ps2', '... ')

        if self.input is sys.stdin:

            # Run PYTHONSTARTUP first.
            st = os.environ.get('PYTHONSTARTUP', '')
            st and eval(builtins.compile(open(st).read(), st, 'exec'), environ)

        while True:

            try:

                buf  = ''

                while not (buf and self.command(buf, environ)):

                    buf += '\n' + input(sys.ps2 if buf else sys.ps1)

            except SystemExit:

                raise

            except EOFError:

                exit()

            except BaseException as e:

                sys.excepthook(type(e), e, self.traceback(e.__traceback__))

