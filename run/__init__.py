import os
import sys
import runpy
import builtins

from .. import parse
from .. import compile


# Preprocess the traceback given its root frame.
#
# :param trace: `Exception.__traceback__`
#
# :return: a new traceback.
#
def traceback(trace):

    uses_runpy = False
    runpy_code = {runpy._run_module_as_main.__code__, runpy._run_code.__code__}

    # Skip over all entries in `runpy` module.
    while trace and trace.tb_frame.f_code in runpy_code:

        trace = trace.tb_next
        uses_runpy = True

    # If `runpy` was used, the next line is in `__main__`.
    trace = trace.tb_next if trace and uses_runpy else trace

    # If the next lines are in this module, skip them, too.
    while trace and trace.tb_frame.f_code is dg.__code__:

        trace = trace.tb_next

    return trace


# Start an interactive shell.
#
# :param name: name of the module.
#
# :return: runs indefinitely.
#
def dg(fd, name='__main__'):

    parser   = parse.r()
    compiler = compile.r()
    environ  = {'__name__': name, '__builtins__': __builtins__}

    if not fd.isatty():

        p = parser.reset(fd.read(), fd.name)
        c = compiler.compile(next(p), name='<module>')
        eval(c, environ)
        return exit(0)

    if fd is sys.stdin:

        # Run PYTHONSTARTUP first.
        st = os.environ.get('PYTHONSTARTUP', '')
        st and eval(builtins.compile(open(st).read(), st, 'exec'), environ)

    sys.ps1 = getattr(sys, 'ps1', '>>> ')
    sys.ps2 = getattr(sys, 'ps2', '... ')
    sys.stdin = fd

    while True:

        try:

            buf  = ''
            code = None

            while not code:

                buf += input(sys.ps2 if buf else sys.ps1)
                tree = parser.compile_command(buf)
                code = tree is not None and compiler.compile(tree, name='<module>')
                buf += '\n'

            sys.displayhook(eval(code, environ))

        except SystemExit:

            raise

        except EOFError:

            exit()

        except BaseException as e:

            sys.excepthook(type(e), e, traceback(e.__traceback__))
