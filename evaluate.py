

def get_token(node):
    return node.__class__.__name__


class EvaluateError(RuntimeError):
    pass


# try to evaluate an expression without executing
def static_evaluate(node, context):
    token = get_token(node)
    if token == 'Num':
        return node.n
    if token == 'Str':
        return node.s
    raise EvaluateError()
