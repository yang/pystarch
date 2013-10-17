

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
class Namespace(object):
    def __init__(self):
        self._levels = []

    def add_name(self, name, typename):
        self._levels[-1][name] = typename

    def gettype(self, name):
        for level in reversed(self._levels):
            if name in level:
                return level[name]
        return None

    def getattr(self, classname, attr, default=None):
        pass

    def push_scope(self, scope={}):
        self._levels.append(scope)

    def pop_scope(self):
        return self._levels.pop()



