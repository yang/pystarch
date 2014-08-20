from backend import get_token


def show_node(node):
    token = get_token(node)
    if token == 'Name':
        return node.id
    if token == 'Call':
        return show_node(node.func)
    if token == 'Attribute':
        return '.' + node.attr
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
    def __init__(self, filepath, node, category, details=None):
        self.filepath = filepath
        self.category = category
        self.node = node
        self.details = details

    def __str__(self):
        extra = ' ({0})'.format(self.details) if self.details else ''
        return self.filepath + ':{0} {1} "{2}"{3}'.format(self.node.lineno,
            self.category, show_node(self.node), extra)


class Warnings(object):
    def __init__(self, filepath):
        self._filepath = filepath
        self._warnings = []

    def set_filepath(self, filepath):
        self._filepath = filepath

    def warn(self, node, category, details=None):
        warning = NodeWarning(self._filepath, node, category, details)
        self._warnings.append(warning)

    def __str__(self):
        return ''.join([str(warning) + '\n' for warning in self._warnings])
