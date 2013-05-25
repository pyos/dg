from .. import parse
from .  import core, bootstrap


def it(st):

    c = core.CodeGenerator('<module>')
    c.loadop('RETURN_VALUE', st, delta=0)
    return c.compiled


def fd(fd, name='<stream>'):

    return it(parse.fd(fd, name))
