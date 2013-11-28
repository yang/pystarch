"""
This file contains "prototypes" for builtins that have the same type
signatures, but have stubbed implementations. Some builtins are commented
out because they are deprecated or not valid in the functional sublanguage.
"""

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

#def apply(func, args, keywords={}):
#    pass

class basestring(object):
    def __init__(self):
        pass

@types(number)
def bin(x):
    return string

def bool(x=False):
    return boolean

#def buffer(obj, offset=number, size=None):
#    pass

def bytearray(source=string, encoding=string, errors=string):
    return [number]

def callable(obj):
    return boolean

@types(number)
def chr(i):
    return string

#def classmethod(func):
#    pass

def cmp(x, y):
    return number

@types(number, number)
def coerce(x, y):
    return (number, number)

#@types(string, string, string, number, number)
#def compile(source, filename, mode, flags=number, dont_inherit=number):
#    pass

@types(number, number)
def complex(real=number, imag=number):
    return number

def delattr(obj, name):
    return None

# TODO: how to support **kwargs when iterable is not specified
def dict(iterable, **kwargs):
    return {a: b for a, b in iterable}

def dir(obj=None):
    return [string]

@types(number, number)
def divmod(a, b):
    return (number, number)

def enumerate(sequence, start=number):
    return [(number, item) for item in sequence]

#def eval(expression, globals, locals):
#    pass

#def execfile(filename, globals, locals):
#    pass

class file(object):
    def __init__(self, name, mode=string, buffering=number):
        self.closed = boolean
        self.encoding = string
        self.errors = string
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

def filter(func, iterable):
    return iterable

def float(x):
    return number

def format(value, format_spec=string):
    return string

def frozenset(iterable):
    return {x for x in iterable}

#def getattr(obj, name, default=None):
#    return anytype

#def globals():
#    return {string: anytype}

def hasattr(obj, name):
    return boolean

def hash(obj):
    return number

def help(obj=None):
    return string

@types(number)
def hex(number):
    return string

def id(obj):
    return number

#def __import__(name, globals={}, locals={}, fromlist=[], level=number):
#    pass

#@types(string)
#def input(prompt=''):
#    pass

def int(x):
    return number

@types(string)
def intern(string):
    return string

def isinstance(obj, classinfo):
    return boolean

def issubclass(cls, classinfo):
    return boolean

# TODO: this only supports one of the three modes of iter
class iter(object):
    def __init__(self, func, sentinel):
        self.func = fucn

    def next(self):
        return self.func()

    def __iter__(self):
        return self

def len(s):
    return number

def list(iterable):
    return [x for x in iterable]

#def locals():
#    return {string: anytype}

def long(x):
    return number

def map(func, iterable):
    return [func(x) for x in iterable]

def max(*args, key=lambda x: number):
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

def min(*args, key=lambda x: number):
    return args[0]

def next(iterator, default=ANY):
    return iterator[0]

class object():
    def __init__(self):
        pass

@types(number)
def oct(x):
    return string

@types(string, string, number)
def open(name, mode=string, buffering=number):
    return file(name, mode, buffering)

@types(string)
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

def reduce(func, iterable, initializer=ANY):
    return func(iterable[0], iterable[0])

#def reload():
#    pass

def repr(obj):
    return string

def reversed(seq):
    return seq

@types(number, number)
def round(num, ndigits=number):
    return number

def set(iterable):
    return {x for x in iterable}

def setattr(obj, name, value):
    return None

class slice(object):
    def __init__(self, start, stop, step=number):
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

def sum(iterable, start=number):
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
def xrange(start, stop, step=number):
    return [number]

# TODO: only supports zipping 2 iterables, not arbitrary number
def zip(iterable1, iterable2):
    return [(iterable1[0], iterable2[0])]
