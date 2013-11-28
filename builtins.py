"""
This file contains "prototypes" for builtins that have the same type
signatures, but have stubbed implementations. Some builtins are commented
out because they are deprecated or not valid in the functional sublanguage.
"""

none = None
boolean = True
number = 0
string = ''

@types(number)
def abs(x):
    return number

@types([boolean])
def all(iterable):
    return boolean

@types([boolean])
def any(iterable):
    return boolean

#def apply(function, args, keywords={}):
#    return anytype

@types()
class basestring(object):
    pass

@types(number)
def bin(x):
    return string

def bool(x=False):
    return boolean

#def buffer(obj, offset=0, size=None):
#    return [anytype]

def bytearray(source=string, encoding=string, errors=string):
    return [number]

def callable(obj):
    return boolean

@types(number)
def chr(i):
    return string

# TODO: this is probably wrong
def classmethod(function):
    return function

def cmp(x, y):
    return number

#@types(number, number)
#def coerce(x, y):
#    return (number, number)

#@types(string, string, string, number, number)
#def compile(source, filename, mode, flags=0, dont_inherit=0):
#    return instance

@types(number, number)
def complex(real, imag):
    return number

#def delattr(obj, name):
#    return none

# TODO: how to support **kwargs
def dict(iterable, **kwargs):
    return {a: b for a, b in iterable}

def dir(obj=None):
    return [string]

@types(number, number)
def divmod(a, b):
    return (number, number)

def enumerate(sequence, start=0):
    return [(number, item) for item in sequence]

#def eval(expression, globals, locals):
#    return anytype

#def execfile(filename, globals, locals):
#    return anytype

class file(object):
    def __init__(self, name, mode='r', buffering=0):
        self.closed = boolean
        self.encoding = string
        self.errors = string    # TODO: check this
        self.mode = string
        self.name = string
        self.newlines = string
        self.softspace = boolean

    def close(self):
        return None

    def flush(self):
        return None

    def fileno(self):
        return number

    def isatty(self):
        return boolean

    def next(self):
        return string

    def read(self, size=number):
        return string

    def readline(self, size=number):
        return string

    def readlines(self, sizehint=number):
        return [string]

    def xreadlines(self):
        return [string]

    def seek(self, offset, whence=number):
        return None

    def tell(self);
        return number

    def truncate(self, size=number):
        return None

    def write(self, str):
        return None

    def writelines(self, sequence):
        return None

def filter(function, iterable):
    return iterable

def float(x):
    return number

def format(value, format_spec=None):
    return string

def frozenset(iterable=[]):
    return {x for x in iterable}

#def getattr(obj, name, default=None):
#    return anytype

#def globals():
#    return {string: anytype}

#@types(instance, string)
#def hasattr(obj, name):
#    return boolean

def hash(obj):
    return number

def help(obj=None):
    return string

@types(number)
def hex(number):
    return string

def id(obj):
    return number

#def __import__(name, globals={}, locals={}, fromlist=[], level=-1):
#    return instance

#@types(string)
#def input(prompt=''):
#    return anytype

def int(x):
    return number

#@types(string)
#def intern(string):
#    return string

def isinstance(obj, classinfo):
    return boolean

def issubclass(cls, classinfo):
    return boolean

#def iter(o, sentinel=None):
#    return instance

def len(s):
    return number

def list(iterable):
    return [x for x in iterable]

#def locals():
#    return {string: anytype}

def long(x):
    return number

def map(function, iterable):
    return [function(x) for x in iterable]

def max(*args, key=lambda x: ANY):
    return args[0]

class memoryview(object):
    def __init__(self, obj):
        self.format = string
        self.itemsize = number
        self.shape = (number,) # TODO: can't handle ndim != 1
        self.ndim = number
        self.strides = (number,) # TODO: can't handler ndim != 1
        self.readonly = boolean

    def tobytes(self):
        return string

    def tolist(self):
        return [number]

def min(*args, key=lambda x: ANY):
    return args[0]

def next(iterator, default=ANY):
    return iterator[0]

class object():
    pass

@types(number)
def oct(x):
    return string

@types(string, string, number)
def open(name, mode=string, buffering=number):
    return file(name, mode, buffering)

@types()
def ord(c):
    return number

@types(number, number, number)
def pow(x, y, z=number):
    return number

def print(*objects, sep=string, end=string, file=file()):
    return None

#def property():
#    pass

@types(number, number, number)
def range(start, stop=number, step=number):
    return [number]

@types(string)
def raw_input(prompt=string):
    return string

def reduce(function, iterable, initializer=ANY):
    return function(iterable[0], iterable[0])

#def reload():
#    pass

def repr(obj):
    return string

def reversed(seq):
    return seq

@types(number, number)
def round(num, ndigits=0):
    return number

def set(iterable=[]):
    return {x for x in iterable}

#def setattr():
#    pass

class slice(object):
    def __init__(self, start, stop, step=1):
        self.start = start
        self.stop = stop
        self.step = step

def sorted(iterable, cmp=lambda x,y: number, key=lambda x: number,
        reverse=boolean):
    return iterable

#def staticmethod(func):
#    pass

def str(obj):
    return string

def sum(iterable, start=0):
    return number

def super(classtype, obj):
    return classtype()

#def tuple(iterable):
#    pass

#def type(obj):
#    return pass

@types(number)
def unichr(i):
    return string

def unicode(obj, encoding=string, errors=string):
    return string

#def vars(obj):
#    return {}

@types(number, number, number)
def xrange(start, stop, step=1):
    return [number]

def zip(iterable1, iterable2):
    return [(iterable1[0], iterable2[0])]
