from type_objects import Any

class klass(object):
    pass
functiontype = lambda: 0
anytype = Any()
boolean = True
none = None
number = 0
string = ''

@types(number)
def abs():
    return number

@types([boolean])
def all(iterable):
    return boolean

@types([boolean])
def any(iterable):
    return boolean

# TODO: this is not quite right
@types(functiontype, [anytype], {string: anytype})
def apply(function, args, keywords={}):
    return anytype

# TODO: this is not quite right
@types()
def basestring():
    return klass

@types(number)
def bin(x):
    return string

@types(number)
def bool(x):
    return boolean

# TODO: this is not quite right
@types(instance, number, number)
def buffer(object, offset=0, size=None):
    return [anytype]

# TODO: check types
@types([number], string, string)
def bytearray():
    return [number]

@types(instance)
def callable(object):
    return boolean

@types(number)
def chr(i):
    return string

@types(functiontype)
def classmethod(function):
    return functiontype

@types(number, number)
def cmp(x, y):
    return number

@types(number, number)
def coerce(x, y):
    return (number, number)

@types(string, string, string, number, number)
def compile(source, filename, mode, flags=0, dont_inherit=0):
    return instance

@types(number, number)
def complex(real, imag):
    return number

@types(instance, string)
def delattr(object, name):
    return none

# TODO: this requires templating
@types([(anytype, anytype)])
def dict(iterable=None, **kwargs):
    if iterable is not None:
        return {a: b for a, b in iterable}
    else:
        return kwargs

@types(instance)
def dir(object=None):
    return [string]

@types(number, number)
def divmod(a, b):
    return (number, number)

@types([anytype], number)
def enumerate(sequence, start=0):
    return [(number, anytype)]

@types(string, {string: anytype}, {string: anytype})
def eval(expression, globals, locals):
    return anytype

@types(string, {string: anytype}, {string: anytype})
def execfile(filename, globals, locals):
    return anytype

@types(string, string, number)
def file(name, mode='r', buffering=0):
    return instance

# TODO: needs templating
@types(functiontype, [anytype])
def filter(function, iterable):
    return iterable

@types(string)
def float(x='0'):
    return number

@types(anytype, string)
def format(value, format_spec=None):
    return string

# TODO: needs templating
@types([anytype])
def frozenset(iterable=[]):
    return {anytype}

# TODO: the value depends on the arguments and templating won't help
@types(instance, string, anytype)
def getattr(object, name, default=None):
    return anytype

@types()
def globals():
    return {string: anytype}

@types(instance, string)
def hasattr(object, name):
    return boolean

@types(instance)
def hash(object):
    return number

@types(instance)
def help(object=None):
    return string

@types()
def hex():
@types()
def id():
@types()
def __import__():
@types()
def input():
@types()
def int():
@types()
def intern():
@types()
def isinstance():
@types()
def issubclass():
@types()
def iter():
@types()
def len():
@types()
def list():
@types()
def locals():
@types()
def long():
@types()
def map():
@types()
def max():
@types()
def memoryview():
@types()
def min():
@types()
def next():
@types()
def object():
@types()
def oct():
@types()
def open():
@types()
def ord():
@types()
def pow():
@types()
def print():
@types()
def property():
@types()
def range():
@types()
def raw_input():
@types()
def reduce():
@types()
def reload():
@types()
def repr():
@types()
def reversed():
@types()
def round():
@types()
def set():
@types()
def setattr():
@types()
def slice():
@types()
def sorted():
@types()
def staticmethod():
@types()
def str():
@types()
def sum():
@types()
def super():
@types()
def tuple():
@types()
def type():
@types()
def unichr():
@types()
def unicode():
@types()
def vars():
@types()
def xrange():
@types()
def zip():
