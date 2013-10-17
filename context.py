

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

# import statement creates a whole new scope heirarchy, not just a new level

# type check Attribute(expr, attr):
# classname = expr_type(expr)
# typename = scope.getattr(classname, attr) # 


def builtin_namespace():
    namespace = Namespace()
    namespace.add_symbol('None', 'None')
    namespace.add_symbol('True', 'Bool')
    namespace.add_symbol('False', 'Bool')
    namespace.add_symbol('int', 'Num')
    namespace.add_symbol('float', 'Num')
    namespace.add_symbol('str', 'Str')
    return namespace


class Symbol(object):
    def __init__(self, name, typename, subnamespace, argtypes):
        self.name = name
        self.typename = typename
        self.subnamespace = subnamespace
        self.argtypes = argtypes

    def __str__(self):
        first_line = '{0} {1}'.format(self.typename, self.name)
        if self.argtypes is not None:
            first_line += '({0})'.format(', '.join(self.argtypes))
        remaining = str(self.subnamespace)
        if len(remaining) == 0:
            return first_line
        indented = '\n'.join([2*' ' + line for line in remaining.splitlines()])
        return first_line + '\n' + indented


# class MyClass: # name='MyClass', typename='MyClass', subnamespace=...
# m = MyClass()  # name='m', typename='MyClass', subnamespace=None
# import mymodule # name='mymodule', typename='mymodule', subnamespace=...
class Namespace(object):
    def __init__(self):
        self.symbols = {}

    def add_symbol(self, name, typename, subnamespace=None, argtypes=None):
        self.symbols[name] = Symbol(name, typename,
            subnamespace or Namespace(), argtypes)

    def remove_symbol(self, name):
        self.symbols.pop(name)

    def get_symbol(self, name, default=None):
        return self.symbols.get(name, default)

    def get_type(self, name, default=None):
        symbol = self.get_symbol(name)
        return symbol.typename if symbol else default

    def __contains__(self, name):
        return name in self.symbols

    def __str__(self):
        return '\n'.join([str(symbol) for symbol in self.symbols.itervalues()])


class Context(object):
    def __init__(self):
        self.namespace_layers = [builtin_namespace()]

    def begin_namespace(self):
        self.namespace_layers.append(Namespace())

    def end_namespace(self):
        return self.namespace_layers.pop()

    def get_top_namespace(self):
        return self.namespace_layers[-1]

    def add_symbol(self, name, typename, subnamespace=None, argtypes=None):
        namespace = subnamespace or Namespace()
        return self.get_top_namespace().add_symbol(name, typename,
            namespace, argtypes)

    def remove_symbol(self, name):
        for namespace in reversed(self.namespace_layers):
            if name in namespace:
                namespace.remove_symbol(name)
                return

    def get_symbol(self, name, default=None):
        for namespace in reversed(self.namespace_layers):
            if name in namespace:
                return namespace.get_symbol(name)
        return default

    def get_type(self, name, default=None):
        symbol = self.get_symbol(name)
        return symbol.typename if symbol else default

    # typename is what is passed after evaluating the type of the
    # expresssion on the left hand side of the period operator
    def get_attr_type(self, typename, attr, default=None):
        symbol = self.get_symbol(typename)
        return symbol.subnamespace.get_type(attr) if symbol else default

