from type_objects import NoneType, Bool

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
    return {
        'None': NoneType(),
        'True': Bool(),
        'False': Bool(),
    }


class Context(object):
    def __init__(self, layers=None):
        self._scope_layers = [builtin_scope()] if layers is None else layers

    def copy(self):
        """This makes a copy that won't lose scope layers when the original
        ends scopes, but it will still share the data structure for each
        scope."""
        return Context([scope for scope in self._scope_layers])

    def begin_scope(self):
        self._scope_layers.append({})

    def end_scope(self):
        return self._scope_layers.pop()

    def get_top_scope(self):
        return self._scope_layers[-1]

    def add_symbol(self, name, symbol_type):
        self.get_top_scope()[name] = symbol_type

    def merge_scope(self, scope):
        self.get_top_scope().update(scope)

    def remove_symbol(self, name):
        for scope in reversed(self._scope_layers):
            if name in scope:
                del scope[name]
                return

    def get_type(self, name, default=None):
        for scope in reversed(self._scope_layers):
            if name in scope:
                return scope[name]
        return default

    def __str__(self):
        return '\n'.join([
            '\n'.join([name + ' ' + str(typ) for name, typ in layer.items()])
            for layer in self._scope_layers])


class ExtendedContext(Context):
    """ This class gives you a context that you can use and modify normally,
        but which extends a base context that you cannot modify. """
    def __init__(self, base_context):
        self._base_context = base_context
        super(ExtendedContext, self).__init__([{}])

    def copy(self):
        raise RuntimeError('copy is not allowed on ' + self.__class__.__name__)

    def get_type(self, name, default=None):
        extended_type = super(ExtendedContext, self).get_type(name)
        if extended_type is not None:
            return extended_type
        else:
            return self._base_context.get_type(name, default)

    def __str__(self):
        extended = super(ExtendedContext, self).__str__()
        return str(self._base_context) + '\n' + extended
