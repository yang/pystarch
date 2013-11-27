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

@types()
def delattr():
@types()
def dict():
@types()
def dir():
@types()
def divmod():
@types()
def enumerate():
@types()
def eval():
@types()
def execfile():
@types()
def file():
@types()
def filter():
@types()
def float():
@types()
def format():
@types()
def frozenset():
@types()
def getattr():
@types()
def globals():
@types()
def hasattr():
@types()
def hash():
@types()
def help():
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
