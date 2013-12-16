

def get_token(node):
    return node.__class__.__name__


class UnknownValue(object):
    def __str__(self):
        return self.__class__.__name__


# try to evaluate an expression without executing
def static_evaluate(node, context):
    token = get_token(node)
    if token == 'Num':
        return node.n
    if token == 'Str':
        return node.s
    if token == 'Name':
        value = context.get_value(node.id, UnknownValue())
        if not isinstance(value, UnknownValue):
            return value
    return UnknownValue()
