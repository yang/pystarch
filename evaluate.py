import expr
from functools import partial
from numbers import Number
from operators import get_operator_function
from type_objects import Instance


def get_token(node):
    return node.__class__.__name__


class UnknownValue(object):
    def __str__(self):
        return self.__class__.__name__


def operator_evaluate(operator, *args):
    func = get_operator_function(operator)
    if func is None:
        raise RuntimeError('Unrecognized operator: ' + operator)
    try:
        return func(*args)
    except (TypeError, ValueError):
        return UnknownValue()


# try to evaluate an expression without executing
def static_evaluate(node, context):
    token = get_token(node)
    recur = partial(static_evaluate, context=context)
    if token == 'Num':
        return node.n
    if token == 'Str':
        return node.s
    if token == 'Name':
        return context.get_value(node.id, UnknownValue())
    if token == 'BoolOp':
        operator = get_token(node.op)
        return operator_evaluate(operator, *map(recur, node.values))
    if token == 'UnaryOp':
        operator = get_token(node.op)
        return operator_evaluate(operator, recur(node.operand))
    if token == 'BinOp':
        operator = get_token(node.op)
        return operator_evaluate(operator, recur(node.left), recur(node.right))
    if token == 'Compare':
        values = [recur(node.left)] + map(recur, node.comparators)
        operators = map(get_token, node.ops)
        assert len(values) == len(operators) + 1
        results = [operator_evaluate(operators[i], values[i], values[i+1])
            for i in range(len(operators))]
        return operator_evaluate('And', *results)
    if token == 'List':
        return list(map(recur, node.elts))
    if token == 'Set':
        return set(map(recur, node.elts))
    if token == 'Dict':
        return dict(zip(map(recur, node.keys), map(recur, node.values)))
    if token == 'Tuple':
        return tuple(map(recur, node.elts))
    if token == 'IfExp':
        test = recur(node.test)
        if test is True:
            return recur(node.body)
        if test is False:
            return recur(node.orelse)
    if token == 'Attribute':
        value_type = expr.expression_type(node.value, context)
        if isinstance(value_type, Instance):
            return value_type.attributes.get_value(node.attr, UnknownValue())
    return UnknownValue()
