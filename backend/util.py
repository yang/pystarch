from type_objects import NoneType, Maybe, Unknown


def known_types(types):
    return set([x for x in types if not isinstance(x, Unknown)])


def unique_type(types):
    known = known_types(types)
    return iter(known).next() if len(known) == 1 else Unknown()


def unify_types(a, b):
    unique = unique_type([a, b])
    if unique != Unknown():
        return unique
    elif isinstance(a, NoneType):
        return b if isinstance(b, Maybe) else Maybe(b)
    elif isinstance(b, NoneType):
        return a if isinstance(a, Maybe) else Maybe(a)
    else:
        return Unknown()


def comparable_types(a, b):
    if a == b or isinstance(a, Unknown) or isinstance(b, Unknown):
        return True
    if isinstance(a, Maybe):
        if isinstance(b, (NoneType, a.subtype)):
            return True
    if isinstance(b, Maybe):
        if isinstance(a, (NoneType, b.subtype)):
            return True
    return False


def type_subset(types, classes):
    return all(any(isinstance(t, c) for c in classes) for t in types)


def type_set_match(types, classes):
    known = known_types(types)
    unmatched = [x for x in classes
        if not any(isinstance(y, x) for y in types)]
    unknowns = [x for x in types if isinstance(x, Unknown)]
    return type_subset(known, classes) and len(unknowns) >= len(unmatched)


def first_type(types):
    for typ in types:
        if isinstance(typ, Maybe):
            return typ.subtype
        elif isinstance(typ, NoneType):
            continue
        return typ
    return NoneType


def consistent_types(types, allow_maybe=True):
    known = known_types(types)
    base_type = first_type(known)
    options = ([base_type, Maybe(base_type), NoneType()]
                if allow_maybe else [base_type])
    return all(any(typ == x for x in options) for typ in known)

