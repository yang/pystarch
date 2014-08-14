from functools import partial
from type_objects import Unknown, Bool, Num, Str, List, Dict,
    Function, Class

# TODO: have to take intersection of types if one symbols appears
# multiple times in the expression

def get_token(node):
    return node.__class__.__name__


def flatten(lists):
    return [a for l in lists for a in l]


def find_constraints(node, result_type, context):
    recur = partial(find_constraints, context=context)
    token = get_token(node)
    if token == 'BoolOp':
        return flatten([recur(x, Bool()) for x in node.values])
    if token == 'BinOp':
        return recur(node.left, Num()) + recur(node.right, Num())
    if token == 'UnaryOp':
        return recur(node.operand, Num())
    if token == 'Lambda':
        return recur(node.body, result_type)
    if token == 'IfExp':
        return (recur(node.test, Bool())
                + recur(node.body, result_type)
                + recur(node.orelse, result_type))
    if token == 'Dict':
        return []
    if token == 'Set':
        return []
    if token == 'ListComp':
        return []
    if token == 'SetComp':
        return []
    if token == 'DictComp':
        return []
    if token == 'GeneratorExp':
        return []
    if token == 'Yield':
        return []
    if token == 'Compare':
        return recur(node.left, Num()) + flatten([recur(x, Num())
            for x in node.comparators)
    if token == 'Call':
        func_type = expression_type(node.func, context)
        if not isinstance(func_type, (Function, Class)):
            return []
        arg_types = func_type.arguments.types
        # TODO: handle keyword arguments
        return (flatten([recur(x, y) for x, y in zip(node.args, arg_types)])
                + recur(node.starargs, List(Unknown()))
                + recur(node.kwargs, Dict(Unknown(), Unknown())))
    if token == 'Repr':
        return []
    if token == 'Num':
        return []
    if token == 'Str':
        return []
    if token == 'Attribute':
        return []
    if token == 'Subscript':
        return []   # TODO: check type of slice
    if token == 'Name':
        return ([(node.id, return_type)]
                if not isinstance(return_type, Unknown) else None)
    if token == 'List':
        if isinstance(return_type, List):
            return flatten([recur(x, return_type.subtype) for x in node.elts])
        else:
            return []
    if token == 'Tuple':
        if isinstance(return_type, Tuple):
            return flatten([recur(x, y) for x, y
                            in zip(node.elts, return_type.subtypes)])
        else:
            return []
    raise 'Unrecognized expression token: ' + token
