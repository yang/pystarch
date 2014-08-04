
class EqualityMixin(object):
    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))


class BasicMixin(object):
    def __str__(self):
        return self.__class__.__name__

class ItemTypeMixin(object):
    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__, self.item_type)

class TupleMixin(object):
    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__,
            ','.join([str(x) for x in self.item_types]))

class CallableMixin(object):
    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__,
            self.arguments)


class Unknown(EqualityMixin, BasicMixin):
    def example(self):
        return object()

class NoneType(EqualityMixin, BasicMixin):
    def example(self):
        return None

class Bool(EqualityMixin, BasicMixin):
    def example(self):
        return True

class Num(EqualityMixin, BasicMixin):
    def example(self):
        return 1

class Str(EqualityMixin, BasicMixin):
    def example(self):
        return 'a'

class List(EqualityMixin, ItemTypeMixin):
    def __init__(self, item_type):
        self.item_type = item_type

    def example(self):
        return [self.item_type.example()]

class Tuple(EqualityMixin, TupleMixin):
    def __init__(self, item_types):
        self.item_types = item_types

    def example(self):
        return tuple(x.example() for x in self.item_types)

class Set(EqualityMixin, ItemTypeMixin):
    def __init__(self, item_type):
        self.item_type = item_type

    def example(self):
        return {self.item_type.example()}

class Dict(EqualityMixin):
    def __init__(self, key_type, value_type):
        self.key_type = key_type
        self.value_type = value_type

    def example(self):
        return {self.key_type.example(): self.value_type.example()}

    def __str__(self):
        return '{0}({1},{2})'.format(self.__class__.__name__,
            self.key_type, self.value_type)

class Function(EqualityMixin, CallableMixin):
    def __init__(self, arguments, return_type):
        self.arguments = arguments
        self.return_type = return_type

    def example(self):
        return object()

# set class_name to __import__ for imports
class Instance(EqualityMixin):
    def __init__(self, class_name, attributes):
        self.class_name = class_name
        self.attributes = attributes

    def example(self):
        return object()

    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__, self.class_name)

# a Class is a Function that returns an Instance plus static methods/attrs
class Class(EqualityMixin, CallableMixin):
    def __init__(self, arguments, return_type, attributes):
        self.arguments = arguments
        self.return_type = return_type
        # symbols only contains class methods and class attributes
        self.attributes = attributes

    def example(self):
        return object()

class Maybe(EqualityMixin):
    def __init__(self, subtype):
        self.subtype = subtype

    def example(self):
        return self.subtype.example()

    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__, self.subtype)


class Union(EqualityMixin):
    def __init__(self, *subtypes):
        assert len(subtypes) > 0
        self.subtypes = subtypes

    def example(self):
        return self.subtypes[0].example()

    def __str__(self):
        return 'Union({0})'.format(','.join([str(x) for x in self.subtypes]))
