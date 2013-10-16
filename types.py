import ast


def get_token(node):
    return node.__class__.__name__


def expression_type(node, scope):
    token = get_token(node)
    mapping = {
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


class Visitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)
        self._warnings = []
        self._scopes = [{'None': 'None', 'True': 'Bool', 'False': 'Bool'}]

    def warnings(self):
        return self._warnings

    def warn(self, category, what, lineno, details=None):
        self._warnings.append((category, what, lineno, details))

    def set_scope(self, name, value):
        self._scopes[-1][name] = value

    def scope(self):
        flat_scope = {}
        for scope in self._scopes:
           flat_scope.update(scope)
        return flat_scope

    def eval_type(self, node):
        return expression_type(node, self.scope())

    def visit_scope(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        return self._scopes.pop()

    def visit_Module(self, node):
        self.visit_scope(node)

    def visit_FunctionDef(self, node):
        scope = self.visit_scope(node)
        self.set_scope(node.name, scope.get('__return__', 'None'))

    def visit_Return(self, node):
        self.assign('__return__', node.value, allow_reassign=True)

    def consistent_types(self, nodes, what):
        types = [self.eval_type(node) for node in nodes]
        # TODO: make another warning that allows nonetype
        if len(set(types)) > 1:
            details = ', '.join(types)
            self.warn('inconsitent-types', what, nodes[0].lineno, details)

    def visit_BoolOp(self, node):
        self.consistent_types(node.values, node.op)

    def visit_Compare(self, node):
        nodes = [node.left] + node.comparators
        tokens = [get_token(op) for op in node.ops]
        self.consistent_types(nodes, ' '.join(tokens))

    def assign(self, name, value, allow_reassign=False):
        new_type = self.eval_type(value)
        previous_type = self.scope().get(name)
        if previous_type is not None:
            if previous_type != new_type:
                details = '{0} -> {1}'.format(previous_type, new_type)
                if previous_type == 'None' or new_type == 'None':
                    self.warn('maybe-type', name, value.lineno, details)
                else:
                    self.warn('type-change', name, value.lineno, details)
            if not allow_reassign:
                self.warn('reassignment', name, value.lineno)
        self.set_scope(name, new_type)

    def visit_Assign(self, node):
        for target in node.targets:
            self.assign(target.id, node.value)


def main():
    filename = 'testcase.py'
    with open(filename) as test_case:
        source = test_case.read()
    tree = ast.parse(source, filename)
    visitor = Visitor()
    visitor.visit(tree)
    warnings = visitor.warnings()
    for warning in warnings:
        message = '{0}: {1} on line {2}'.format(*warning[:3])
        print message + ' ({0})'.format(warning[3]) if warning[3] else message


if __name__ == '__main__':
    main()
