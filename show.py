from expr import get_token


def show_node(node):
    token = get_token(node)
    if token == 'Name':
        return node.id
    if token == 'Call':
        return node.func.id
    if token == 'Attribute':
        return '.' + node.attr.id
    if token in ['BoolOp', 'BinOp', 'UnaryOp']:
        return get_token(node.op)
    if token == 'Assign':
        return show_node(node.targets[0]) + ' = ...'
    if token == 'AugAssign':
        return show_node(node.target) + ' = ...'
    if token == 'Compare':
        return ' '.join([get_token(op) for op in node.ops])
    return token

