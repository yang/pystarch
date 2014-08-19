import copy
from type_objects import NoneType, Bool
from evaluate import UnknownValue
from util import type_intersection

# Tricky: need to support obj1.obj2.x where obj2 is an instance
# of a class that may not be defined in the current scope
# Idea: maintain a separate scope dict that contains all the class
# type data, keyed by classname
# Assume that all attributes are either set in __init__ or method names

# Also, if we import one function from another module, and that function
# calls another function that was not imported, we need to know the type
# of the other function without having it in our scope. Perhaps we should
# maintain two scopes. One for everything that is loaded, another for
# everything that is in scope. LoadScope vs. NameScope
# Whenever you add to LoadScope, it automatically adds to NameScope,
# but not the other way around.


def builtin_scope():
    scope = Scope()
    scope.add(Symbol('None', NoneType(), None))
    scope.add(Symbol('True', Bool(), True))
    scope.add(Symbol('False', Bool(), False))
    return scope


class Symbol(object):
    def __init__(self, name, type_=None, value=None):
        assert name is not None
        assert type_ is not None
        self.assign(name, type_, value)

    def assign(self, name, type_, value):
        self._name = name
        self._type = type_
        self._value = value if type_ != NoneType() else None
        self._assign_expression = None

    def get_name(self):
        return self._name

    def get_type(self):
        return self._type

    def get_value(self):
        return self._value

    def add_constraint(self, type_, recur):
        new_type = type_intersection(self._type, type_)
        if new_type is not None:
            # problem: do we have to maintain the definition context
            # for every symbol? that's way too much memory
            if self._assign_expression is not None:
                recur(self._assign_expression, new_type)
            self._type = new_type
            return new_type
        else:
            return None

    def __str__(self):
        if isinstance(self._value, UnknownValue):
            return str(self._type)
        return '{0} {1}'.format(self._type, self._value)


class Scope(object):
    def __init__(self):
        self._symbols = {}
        self._return = None

    def __hash__(self):
        return hash(frozenset(self._symbols.items())) + hash(self._return)

    def names(self):
        return self._symbols.keys()

    def symbols(self):
        return copy.copy(self._symbols)

    def get(self, name):
        return self._symbols.get(name)

    def get_type(self, name=None):
        symbol = self.get(name) if name else self.get_return()
        return symbol.get_type() if symbol else None

    def add(self, symbol):
        assert isinstance(symbol, Symbol)
        self._symbols[symbol.get_name()] = symbol

    def remove(self, name):
        del self._symbols[name]

    def merge(self, scope):
        assert isinstance(scope, Scope)
        self._symbols.update(scope.symbols())

    def set_return(self, symbol):
        assert isinstance(symbol, Symbol)
        self._return = symbol

    def get_return(self):
        return self._return

    def __str__(self):
        fmt = lambda name, sym: '{0} {1}'.format(name, sym)
        end = '\n' if len(self._symbols) > 0 else ''
        return '\n'.join([fmt(name, self._symbols[name])
            for name in sorted(self._symbols.keys())]) + end

    def __contains__(self, name):
        return name in self._symbols


class Context(object):
    def __init__(self, layers=None):
        self._scope_layers = [builtin_scope()] if layers is None else layers

    def __str__(self):
        return '\n'.join([str(layer) for layer in self._scope_layers])

    def __contains__(self, name):
        return any(name in scope for scope in self._scope_layers)

    def copy(self):
        """This makes a copy that won't lose scope layers when the original
        ends scopes, but it will still share the data structure for each
        scope."""
        return Context([scope for scope in self._scope_layers])

    def begin_scope(self):
        self._scope_layers.append(Scope())

    def end_scope(self):
        if len(self._scope_layers) <= 1:
            raise RuntimeError('Cannot close bottom scope layer')
        return self._scope_layers.pop()

    def get_top_scope(self):
        return self._scope_layers[-1]

    def add(self, symbol):
        assert isinstance(symbol, Symbol)
        self.get_top_scope().add(symbol)

    def remove(self, name):
        scope = self.find_scope(name)
        if scope is not None:
            scope.remove(name)

    def get(self, name):
        scope = self.find_scope(name)
        return scope.get(name) if scope is not None else None

    def get_type(self, name=None):
        symbol = self.get(name) if name else self.get_return()
        return symbol.get_type() if symbol else None

    def set_return(self, symbol):
        self.get_top_scope().set_return(symbol)

    def get_return(self):
        return self.get_top_scope().get_return()

    def merge_scope(self, scope):
        self.get_top_scope().merge(scope)

    def find_scope(self, name):
        for scope in reversed(self._scope_layers):
            if name in scope:
                return scope
        return None


class ExtendedContext(Context):
    """ This class gives you a context that you can use and modify normally,
        but which extends a base context that you cannot modify. """
    def __init__(self, base_context):
        self._base_context = base_context
        super(ExtendedContext, self).__init__([Scope()])

    def __contains__(self, name):
        return (super(ExtendedContext, self).__contains__(name)
                or (name in self._base_context))

    def copy(self):
        raise RuntimeError('copy is not allowed on ' + self.__class__.__name__)

    def get(self, name):
        extended = super(ExtendedContext, self).get(name)
        if extended is not None:
            return extended
        else:
            return self._base_context.get(name)

    def __str__(self):
        extended = super(ExtendedContext, self).__str__()
        return str(self._base_context) + '\n' + extended
