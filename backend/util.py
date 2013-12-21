import ast
from type_objects import NoneType, Maybe, Unknown
from expr import known_types
from evaluate import static_evaluate, UnknownValue


class Visitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)
        self.names = []

    def visit_Name(self, node):
        self.names.append(node.id)


def get_names(node):
    visitor = Visitor()
    visitor.visit(node)
    return visitor.names


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


def maybe_inferences(test, context):
    types = {name: context.get_type(name) for name in get_names(test)}
    maybes = {k: v for k, v in types.items() if isinstance(v, Maybe)}

    if_inferences = {}
    else_inferences = {}
    for name, maybe_type in maybes.items():
        context.begin_scope()
        context.add_symbol(name, NoneType(), None)
        none_value = static_evaluate(test, context)
        context.end_scope()
        if none_value is False:
            if_inferences[name] = maybe_type.subtype
        if none_value is True:
            else_inferences[name] = maybe_type.subtype
        context.begin_scope()
        context.add_symbol(name, maybe_type.subtype, UnknownValue())
        non_none_value = static_evaluate(test, context)
        context.end_scope()
        if non_none_value is False:
            if_inferences[name] = NoneType()
        if non_none_value is True:
            else_inferences[name] = NoneType()
    return if_inferences, else_inferences

