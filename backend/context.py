import copy
from type_objects import NoneType, Bool, Unknown
from evaluate import UnknownValue

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
    scope.add_symbol('None', NoneType(), None)
    scope.add_symbol('True', Bool(), True)
    scope.add_symbol('False', Bool(), False)
    return scope


class Symbol(object):
    def __init__(self, name, type_, value):
        self.assign(name, type_, value)
        self._constraint = AnyType()    # NOTE: won't work well if reassigned

    def assign(self, name, type_, value):
        self._name = name
        self._type = type_
        self._value = value if type_ != NoneType() else None

    def get_name(self):
        return self._name

    def get_type(self):
        return self._type

    def get_value(self):
        return self._value

    def add_constraint(self, type_):
        self._constraint = type_   # TODO: set to intersection

    def __str__(self):
        if isinstance(self._value, UnknownValue):
            return str(self._type)
        else:
            return str(self._type) + ' ' + str(self._value)


class Scope(object):
    def __init__(self):
        self._symbols = {}
        self._return = None

    def names(self):
        return self._symbols.keys()

    def symbols(self):
        return copy.copy(self._symbols)

    def get(self, name):
        return self._symbols.get(name)

    def add(self, symbol):
        self._symbols[symbol.get_name()] = symbol

    def remove(self, name):
        del self._symbols[name]

    def merge(self, scope):
        self._symbols.update(scope.symbols())

    def set_return(self, symbol):
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
        self._type_inferences = {}

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
        self._type_inferences = {}
        if len(self._scope_layers) <= 1:
            raise RuntimeError('Cannot close bottom scope layer')
        return self._scope_layers.pop()

    def get_top_scope(self):
        return self._scope_layers[-1]

    def apply_type_inferences(self, type_inferences):
        self._type_inferences.update(type_inferences)

    def add(self, symbol):
        self.get_top_scope().add(symbol)

    def remove(self, name):
        scope = self.find_scope(name)
        if scope is not None:
            scope.remove(name)

    def get(self, name):
        if name in self._type_inferences:
            return self._type_inferences.get(name)
        scope = self.find_scope(name)
        return scope.get(name) if scope is not None else None

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
        super(ExtendedContext, self).__init__([{}])

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
