import os
import glob

from . import __path__
from pygments.token import *
from pygments.lexer import RegexLexer, combined
from pygments.lexers import LEXERS, get_lexer_by_name

import dmark

__all__ = ['DgLexer']

LEXERS['DgLexer'] = '__main__', 'dg', ('dg',), ('*.dg',), ('text/x-dg',)


class DgLexer(RegexLexer):
    """
    Lexer for `dg <http://pyos.github.com/dg>`_,
    a functional and object-oriented programming language
    running on the CPython 3 VM.
    """
    name = 'dg'
    aliases = ['dg']
    filenames = ['*.dg']
    mimetypes = ['text/x-dg']

    tokens = {
        'root': [
            # Whitespace:
            (r'\s+', Text),
            (r'#.*?$', Comment.Single),
            # Lexemes:
            #  Numbers
            (r'0[bB][01]+', Number.Bin),
            (r'0[oO][0-7]+', Number.Oct),
            (r'0[xX][\da-fA-F]+', Number.Hex),
            (r'[+-]?\d+\.\d+([eE][+-]?\d+)?[jJ]?', Number.Float),
            (r'[+-]?\d+[eE][+-]?\d+[jJ]?', Number.Float),
            (r'[+-]?\d+[jJ]?', Number.Integer),
            #  Character/String Literals
            (r"[br]*'''", String, combined('stringescape', 'tsqs', 'string')),
            (r'[br]*"""', String, combined('stringescape', 'tdqs', 'string')),
            (r"[br]*'", String, combined('stringescape', 'sqs', 'string')),
            (r'[br]*"', String, combined('stringescape', 'dqs', 'string')),
            #  Operators
            (r"`\w+'*`", Operator), # Infix links
            #   Reserved infix links
            (r'\b(or|and|if|unless|else|where|is|in)\b', Operator.Word),
            (r'[!$%&*+\--/:<-@\\^|~;,]+', Operator),
            #  Identifiers
            #   Python 3 types
            (r"(?<!\.)(bool|bytearray|bytes|classmethod|complex|dict'?|"
             r"float|frozenset|int|list'?|memoryview|object|property|range|"
             r"set'?|slice|staticmethod|str|super|tuple'?|type)"
             r"(?!['\w])", Name.Builtin),
            #   Python 3 builtins + some more
            (r'(?<!\.)(__import__|abs|all|any|bin|bind|chr|cmp|compile|complex|'
             r'delattr|dir|divmod|drop|dropwhile|enumerate|eval|filter|flip|'
             r'foldl1?|format|fst|getattr|globals|hasattr|hash|head|hex|id|'
             r'init|input|isinstance|issubclass|iter|iterate|last|len|locals|'
             r'map|max|min|next|oct|open|ord|pow|print|repr|reversed|round|'
             r'setattr|scanl1?|snd|sorted|sum|tail|take|takewhile|vars|zip)'
             r"(?!['\w])", Name.Builtin),
            (r"(?<!\.)(self|Ellipsis|NotImplemented|None|True|False)(?!['\w])",
             Name.Builtin.Pseudo),
            (r"(?<!\.)[A-Z]\w*(Error|Exception|Warning)'*(?!['\w])",
             Name.Exception),
            (r"(?<!\.)(KeyboardInterrupt|SystemExit|StopIteration|"
             r"GeneratorExit)(?!['\w])", Name.Exception),
            #   Compiler-defined identifiers
            (r"(?<![\.\w])(import|inherit|for|while|switch|not|raise|unsafe|"
             r"yield|with)(?!['\w])", Keyword.Reserved),
            #   Other links
            (r"[A-Z_']+\b", Name),
            (r"[A-Z][\w']*\b", Keyword.Type),
            (r"\w+'*", Name),
            #  Blocks
            (r'[()]', Punctuation),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N{.*?}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'string': [
            (r'%(\([a-zA-Z0-9_]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[diouxXeEfFgGcrs%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String),
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop')
        ],
        'sqs': [
            (r"'", String, '#pop')
        ],
        'tdqs': [
            (r'"""', String, '#pop')
        ],
        'tsqs': [
            (r"'''", String, '#pop')
        ],
    }


name_of = lambda x: os.path.basename(x)[:-3]  # - '.md'
files   = glob.glob(os.path.join(__path__[0], '*.md'))
data    = {name_of(x): dmark.parse(open(x).read()) for x in files}

for f in glob.glob(os.path.join(__path__[0], '*.html')):

    src = open(f)
    tgt = open(os.path.join(os.path.dirname(f), os.pardir, os.path.basename(f)), 'w')
    tgt.write(src.read().format(**data))
