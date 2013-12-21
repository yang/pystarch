from type_objects import NoneType, Bool
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


def format_symbol(symbol):
    if isinstance(symbol[1], UnknownValue):
        return str(symbol[0])
    else:
        return str(symbol[0]) + ' ' + str(symbol[1])


class Scope(object):
    def __init__(self):
        self._symbols = {}
        self._return_type = None
        self._return_value = None

    def __str__(self):
        fmt = lambda name, sym: '{0} {1}'.format(name, format_symbol(sym))
        end = '\n' if len(self._symbols) > 0 else ''
        return '\n'.join([fmt(name, self._symbols[name])
            for name in sorted(self._symbols.keys())]) + end

    def __contains__(self, name):
        return name in self._symbols

    def names(self):
        return self._symbols.keys()

    def add_symbol(self, name, typ, value=UnknownValue()):
        val = None if typ == NoneType() else value
        self._symbols[name] = (typ, val)

    def remove_symbol(self, name):
        del self._symbols[name]

    def copy_symbol(self, scope, name):
        self.add_symbol(name, scope.get_type(name), scope.get_value(name))

    def get_type(self, name, default=None):
        return self._symbols[name][0] if name in self._symbols else default

    def get_value(self, name, default=UnknownValue()):
        return self._symbols[name][1] if name in self._symbols else default

    def set_return(self, return_type, return_value=UnknownValue()):
        self._return_type = return_type
        self._return_value = return_value

    def get_return_type(self):
        return self._return_type

    def get_return_value(self):
        return self._return_value

    def merge(self, scope):
        self._symbols.update(scope._symbols)


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

    def add_symbol(self, name, symbol_type, value=UnknownValue()):
        self.get_top_scope().add_symbol(name, symbol_type, value)

    def set_return(self, return_type, return_value=UnknownValue()):
        self.get_top_scope().set_return(return_type, return_value)

    def get_return_type(self):
        return self.get_top_scope().get_return_type()

    def get_return_value(self):
        return self.get_top_scope().get_return_value()

    def copy_symbol(self, scope, name):
        self.get_top_scope().copy_symbol(scope, name)

    def merge_scope(self, scope):
        self.get_top_scope().merge(scope)

    def find_scope(self, name):
        for scope in reversed(self._scope_layers):
            if name in scope:
                return scope
        return None

    def remove_symbol(self, name):
        scope = self.find_scope(name)
        if scope is not None:
            scope.remove_symbol(name)

    def get_type(self, name, default=None):
        if name in self._type_inferences:
            return self._type_inferences[name]
        scope = self.find_scope(name)
        return scope.get_type(name, default) if scope is not None else default

    def get_value(self, name, default=UnknownValue()):
        if name in self._type_inferences:
            if isinstance(self._type_inferences[name], NoneType):
                return None
        scope = self.find_scope(name)
        return scope.get_value(name, default) if scope is not None else default


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

    def get_type(self, name, default=None):
        extended_type = super(ExtendedContext, self).get_type(name)
        if extended_type is not None:
            return extended_type
        else:
            return self._base_context.get_type(name, default)

    def get_value(self, name, default=UnknownValue()):
        extended_value = super(ExtendedContext, self).get_value(name, default)
        if extended_value != default:
            return extended_value
        else:
            return self._base_context.get_value(name, default)

    def __str__(self):
        extended = super(ExtendedContext, self).__str__()
        return str(self._base_context) + '\n' + extended
