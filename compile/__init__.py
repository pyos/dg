from .. import parse
from .  import core, bootstrap


def it(st):

    return ast(parse.it(st))


def fd(fd, name='<stream>'):

    return ast(parse.fd(fd, name))


def ast(st):

    c = core.CodeGenerator('<module>')
    c.loadop('RETURN_VALUE', st, delta=0)
    return c.compiled
