
class EqualityMixin(object):
    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

class BasicMixin(object):
    def __str__(self):
        return self.__class__.__name__

class ItemTypeMixin(object):
    def __str__(self):
        return '{0}[{1}]'.format(self.__class__.__name__, self.item_type)

class TupleMixin(object):
    def __str__(self):
        return '{0}[{1}]'.format(self.__class__.__name__,
            ','.join([str(x) for x in self.item_types]))

class CallableMixin(object):
    def __str__(self):
        return '{0}[{1} -> {2}]'.format(self.__class__.__name__,
            self.arg_types, self.return_type)


class Undefined(EqualityMixin, BasicMixin): pass
class Any(EqualityMixin, BasicMixin): pass
class NoneType(EqualityMixin, BasicMixin): pass
class Bool(EqualityMixin, BasicMixin): pass
class Num(EqualityMixin, BasicMixin): pass
class Str(EqualityMixin, BasicMixin): pass

class List(EqualityMixin, ItemTypeMixin):
    def __init__(self, item_type):
        self.item_type = item_type

class Tuple(EqualityMixin, TupleMixin):
    def __init__(self, item_types):
        self.item_types = item_types

class Set(EqualityMixin, ItemTypeMixin):
    def __init__(self, item_type):
        self.item_type = item_type

class Dict(EqualityMixin):
    def __init__(self, key_type, value_type):
        self.key_type = key_type
        self.value_type = value_type

    def __str__(self):
        return '{0}[{1},{2}]'.format(self.__class__.__name__,
            self.key_type, self.value_type)

class Function(EqualityMixin, CallableMixin):
    def __init__(self, arguments, return_type):
        self.arguments = arguments
        self.return_type = return_type

# set class_name to __import__ for imports
class Instance(EqualityMixin):
    def __init__(self, class_name, attributes):
        self.class_name = class_name
        self.attributes = attributes

    def __str__(self):
        return '{0}[{1}]'.format(self.__class__.__name__, self.class_name)

# a Class is a Function that returns an Instance plus static methods/attrs
class Class(EqualityMixin, CallableMixin):
    def __init__(self, arguments, return_type, attributes):
        self.arguments = arguments
        self.return_type = return_type
        # symbols only contains class methods and class attributes
        self.attributes = attributes
