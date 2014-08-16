from type_objects import NoneType, Maybe, Unknown, Union, List, Set, \
    Dict, Tuple, BaseTuple
from itertools import tee, izip


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def known_types(types):
    return set([x for x in types if not isinstance(x, Unknown)])


def unique_type(types):
    known = known_types(types)
    return iter(known).next() if len(known) == 1 else Unknown()


def _unify_types(a, b):
    unique = unique_type([a, b])
    if not isinstance(unique, Unknown):
        return unique
    elif isinstance(a, NoneType):
        return b if isinstance(b, Maybe) else Maybe(b)
    elif isinstance(b, NoneType):
        return a if isinstance(a, Maybe) else Maybe(a)
    elif isinstance(a, Maybe) and isinstance(b, a.subtype):
        return a
    elif isinstance(b, Maybe) and isinstance(a, b.subtype):
        return b
    else:
        return Unknown()


# used when types have to be merged such as in if/else expressions
def unify_types(types):
    known = known_types(types)
    if len(known) == 0:
        return Unknown()
    elif len(known) == 1:
        return iter(known).next()
    else:
        return reduce(_unify_types, known)


# concept: is it possible for them to have the same type
def unifiable_types(types):
    if all(isinstance(t, Unknown) for t in types):
        return True
    else:
        return not isinstance(unify_types(types), Unknown)


# concept: is it possible for them the have the same value
def _comparable_types(a, b):
    if a == b:
        return True
    if not unifiable_types([a, b]):
        return False
    if isinstance(a, NoneType) and not isinstance(b, Maybe):
        return False
    if isinstance(b, NoneType) and not isinstance(a, Maybe):
        return False
    return True


# concept: is it possible for them to have equal value
def comparable_types(types):
    known = known_types(types)
    if len(known) < 2:
        return True
    else:
        return all(_comparable_types(a, b) for a, b in pairwise(known))


def type_subset(a, b):
    if isinstance(b, Unknown):
        return True
    if isinstance(a, Unknown):
        return False
    if isinstance(b, Union):
        if isinstance(a, Union):
            return all(any(type_subset(x, y) for y in b.subtypes)
                       for x in a.subtypes)
        else:
            return any(type_subset(a, x) for x in b.subtypes)
    if isinstance(a, List) and isinstance(b, List):
        return type_subset(a.item_type, b.item_type)
    if isinstance(a, Set) and isinstance(b, Set):
        return type_subset(a.item_type, b.item_type)
    if isinstance(a, Tuple) and isinstance(b, BaseTuple):
        return True
    if isinstance(a, Tuple) and isinstance(b, Tuple):
        return (len(a.item_types) == len(b.item_types) and
                all(type_subset(x, y) for x, y
                in zip(a.item_types, b.item_types)))
    if isinstance(a, Dict) and isinstance(b, Dict):
        return (type_subset(a.key_type, b.key_type) and
                type_subset(a.value_type, b.value_type))
    if isinstance(b, Maybe):
        if isinstance(a, NoneType):
            return True
        elif isinstance(a, Maybe):
            return type_subset(a.subtype, b.subtype)
        else:
            return type_subset(a, b.subtype)
    return a == b


def type_patterns(types, patterns):
    return any(all(type_subset(x, y) for x, y in zip(types, pattern))
               for pattern in patterns)


def type_intersection(a, b):
    if a == b:
        return a
    elif isinstance(a, Unknown):
        return b
    elif isinstance(b, Unknown):
        return a
    elif isinstance(a, Union) and isinstance(b, Union):
        common = list(set(a.subtypes) & set(b.subtypes))
        if len(common) == 0:
            return None
        elif len(common) == 1:
            return common[0]
        else:
            return Union(common)
    elif isinstance(a, Union):
        return b if b in a.subtypes else None
    elif isinstance(b, Union):
        return a if a in b.subtypes else None
    else:
        return None
