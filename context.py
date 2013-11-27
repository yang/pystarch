from type_objects import Any, NoneType, Bool, Num, Str, List, Tuple, Set, \
    Dict, Function, Instance, Class, Undefined

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
    def __init__(self):
        self.scope_layers = [builtin_scope()]

    def begin_scope(self):
        self.scope_layers.append({})

    def end_scope(self):
        return self.scope_layers.pop()

    def get_top_scope(self):
        return self.scope_layers[-1]

    def add_symbol(self, name, type):
        self.get_top_scope()[name] = type

    def remove_symbol(self, name):
        for scope in reversed(self.scope_layers):
            if name in scope:
                del scope[name]
                return

    def get_type(self, name, default=None):
        for scope in reversed(self.scope_layers):
            if name in scope:
                return scope[name]
        return default
