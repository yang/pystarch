from functools import partial
from type_objects import Unknown, Bool, Num, Str, List, Dict, \
    Function, Class, Tuple, NoneType
from expr import expression_type
from util import type_intersection


# TODO: have to take intersection of types if one symbols appears
# multiple times in the expression

def get_token(node):
    return node.__class__.__name__


def flatten(lists):
    return [a for l in lists for a in l]


def find_constraints(node, result_type, context):
    if node is None:
        return []
    recur = partial(find_constraints, context=context)
    token = get_token(node)
    if token == 'BoolOp':
        return flatten([recur(x, Bool()) for x in node.values])
    if token == 'BinOp':
        return recur(node.left, Num()) + recur(node.right, Num())
    if token == 'UnaryOp':
        return recur(node.operand, Num())
    if token == 'IfExp':
        return (recur(node.test, Bool())
                + recur(node.body, result_type)
                + recur(node.orelse, result_type))
    if token == 'Dict':
        if isinstance(result_type, Dict):
            return (flatten([recur(x, result_type.key_type)
                             for x in node.keys])
                    + flatten([recur(x, result_type.value_type)
                               for x in node.values]))
        else:
            return []
    if token == 'Set':
        if isinstance(result_type, Set):
            return flatten([recur(x, result_type.item_type)
                            for x in node.elts])
        else:
            return []
    if token == 'ListComp':
        return []
    if token == 'SetComp':
        return []
    if token == 'DictComp':
        return []
    if token == 'GeneratorExp':
        return []
    if token == 'Compare':
        operator = get_token(node.ops[0])
        if operator in ['Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE']:
            # all operands are constrained to have the same type
            # as their intersection
            exprs = [node.left] + node.comparators
            types = [expression_type(expr, context) for expr in exprs]
            intersection = reduce(type_intersection, types)
            return flatten([recur(expr, intersection) for expr in exprs])
        if operator in ['Is', 'IsNot']:
            return recur(node.comparators[0], NoneType())
        if operator in ['In', 'NotIn']:
            # constrain right to list/set of left, and left to instance of right
            left = expression_type(node.left, context)
            right = expression_type(node.right, context)
            result = recur(node.right, Union(List(left), Set(left)))
            if isinstance(left, (List, Set)):
                result += recur(node.left, node.comparators[0].item_type)
            return result
    if token == 'Call':
        func_type = expression_type(node.func, context)
        if not isinstance(func_type, (Function, Class)):
            return []
        arg_types = func_type.arguments.types
        # TODO: handle keyword arguments
        return (flatten([recur(x, y) for x, y in zip(node.args, arg_types)])
                + recur(node.starargs, List(Unknown()))
                + recur(node.kwargs, Dict(Unknown(), Unknown())))
    if token == 'Attribute':
        return []
    if token == 'Subscript':
        return []   # TODO: check type of slice
    if token == 'Name':
        return ([(node.id, result_type)]
                if not isinstance(result_type, Unknown) else None)
    if token == 'List':
        if isinstance(result_type, List):
            return flatten([recur(x, result_type.subtype) for x in node.elts])
        else:
            return []
    if token == 'Tuple':
        if isinstance(result_type, Tuple):
            return flatten([recur(x, y) for x, y
                            in zip(node.elts, result_type.subtypes)])
        else:
            return []
    if token in ['Num', 'Str', 'Repr', 'Lambda', 'Yield']:
        return []
    raise RuntimeError('Unrecognized expression token: ' + token)
