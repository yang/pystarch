from type_objects import NoneType, Maybe, Unknown
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


def type_subset(types, classes):
    return all(any(isinstance(t, c) for c in classes) for t in types)


def type_set_match(types, classes):
    known = known_types(types)
    unmatched = [x for x in classes
        if not any(isinstance(y, x) for y in types)]
    unknowns = [x for x in types if isinstance(x, Unknown)]
    return type_subset(known, classes) and len(unknowns) >= len(unmatched)


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
