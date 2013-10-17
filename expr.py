

def get_token(node):
    return node.__class__.__name__


def expression_type(node, scope):
    token = get_token(node)
    mapping = {
        'Any': 'Any',
        'Num': 'Num',
        'Str': 'Str',
        'Tuple': 'Tuple',
        'List': 'List',
        'Dict': 'Dict',
        'Set': 'Set',
        'Repr': 'Repr',
        'ListComp': 'List',
        'SetComp': 'Set',
        'DictComp': 'Dict',
        'Not': 'Bool',
        'BinOp': 'Num',
        'Invert': 'Num',
        'UAdd': 'Num',
        'USub': 'Num',
        'GeneratorExp': 'Tuple',
        'Compare': 'Bool',
        'Subscript': 'List',
    }
    if token in mapping:
        return mapping[token]
    if token == 'Name':
        return scope.get(node.id, 'Undefined')
    if token == 'Attribute':
        return token    # TODO: implement this
    if token == 'BoolOp':
        return expression_type(node.values[-1], scope)
    if token == 'Lambda':
        return expression_type(node.body)
    if token == 'Yield':
        return expression_type(node.value)
    if token == 'Call':
        return scope.get(node.func.id, 'Undefined')  # TODO: needs to be 2 pass
    raise Exception('evalute_type does not recognize ' + token)

