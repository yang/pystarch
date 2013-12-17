import operator
from numbers import Number


def and_operator(*values):
    if all(value is True for value in values):
        return True
    if any(value is False for value in values):
        return False
    raise TypeError()


def or_operator(*values):
    if any(value is True for value in values):
        return True
    if all(value is False for value in values):
        return False
    raise TypeError()


def add_operator(left, right):
    return left + right


def mod_operator(left, right):
    return left % right


def comparison(func):
    def wrapper(*args):
        types = (Number, set)
        if not any(all(isinstance(x, y) for x in args) for y in types):
            raise TypeError()
        return func(*args)
    return wrapper


def get_operator_function(name):
    lookup = {
        'And': and_operator,
        'Or': or_operator,
        'Add': add_operator,
        'In': operator.contains,
        'Div': operator.truediv,
        'FloorDiv': operator.floordiv,
        'BitAnd': operator.and_,
        'BitXor': operator.xor,
        'Invert': operator.invert,
        'BitOr': operator.or_,
        'Pow': operator.pow,
        'Is': operator.is_,
        'IsNot': operator.is_not,
        'LShift': operator.lshift,
        'Mod': mod_operator,
        'Mult': operator.mul,
        'USub': operator.neg,
        'Not': operator.not_,
        'UAdd': operator.pos,
        'RShift': operator.rshift,
        'Repeat': operator.repeat,  # special
        'Sub': operator.sub,
        'Lt': comparison(operator.lt),
        'LtE': comparison(operator.le),
        'Eq': operator.eq,
        'NotEq': operator.ne,
        'GtE': comparison(operator.ge),
        'Gt': comparison(operator.gt),
    }
    return lookup.get(name)
