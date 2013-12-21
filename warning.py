from backend import get_token


def show_node(node):
    token = get_token(node)
    if token == 'Name':
        return node.id
    if token == 'Call':
        return show_node(node.func)
    if token == 'Attribute':
        return '.' + show_node(node.attr)
    if token in ['BoolOp', 'BinOp', 'UnaryOp']:
        return get_token(node.op)
    if token == 'Assign':
        return show_node(node.targets[0]) + ' = ...'
    if token == 'AugAssign':
        return show_node(node.target) + ' = ...'
    if token == 'Compare':
        return ' '.join([get_token(op) for op in node.ops])
    return token


class NodeWarning(object):
    def __init__(self, filepath, category, node, details=None):
        self.filepath = filepath
        self.category = category
        self.node = node
        self.details = details

    def __str__(self):
        extra = ' ({0})'.format(self.details) if self.details else ''
        return self.filepath + ':{0} {1} "{2}"{3}'.format(self.node.lineno,
            self.category, show_node(self.node), extra)

