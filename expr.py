

def get_token(node):
    return node.__class__.__name__


def expression_type(node, context):
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
        return context.get_type(node.id, 'Undefined')
    if token == 'Attribute':
        typename = expression_type(node.value, context)
        return context.get_attr_type(typename, node.attr)
    if token == 'BoolOp':
        return expression_type(node.values[-1], context)
    if token == 'Lambda':
        return expression_type(node.body, context)
    if token == 'Yield':
        return expression_type(node.value, context)
    if token == 'Call':
        # TODO: needs to be 2 pass
        return expression_type(node.func, context)
    raise Exception('evalute_type does not recognize ' + token)

