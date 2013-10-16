import ast


class Tuple():
    pass


def get_token(node):
    return node.__class__.__name__


def dump(node):
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
        return node.targets[0].id + ' = ...'
    if token == 'AugAssign':
        return node.target.id + ' = ...'
    if token == 'Compare':
        return ' '.join([get_token(op) for op in node.ops])
    return token


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

    def warn(self, category, node, details=None):
        self._warnings.append((category, dump(node), node.lineno, details))

    def set_scope(self, name, value):
        self._scopes[-1][name] = value

    def scope(self):
        flat_scope = {}
        for scope in self._scopes:
           flat_scope.update(scope)
        return flat_scope

    def expr_type(self, node):
        return expression_type(node, self.scope())

    def new_scope(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        return self._scopes.pop()

    def consistent_types(self, root_node, nodes):
        types = [self.expr_type(node) for node in nodes]
        # TODO: make another warning that allows nonetype
        if len(set(types)) > 1:
            details = ', '.join(types)
            self.warn('inconsitent-types', root_node, details)

    def check_type(self, node, typename, category):
        if self.expr_type(node) != typename:
            self.warn(category, node)

    def check_assign(self, node, name, value, allow_reassign=False):
        new_type = self.expr_type(value)
        previous_type = self.scope().get(name)
        if previous_type is not None:
            if previous_type != new_type:
                details = '{0} -> {1}'.format(previous_type, new_type)
                if previous_type == 'None' or new_type == 'None':
                    self.warn('maybe-type', node, details)
                else:
                    self.warn('type-change', node, details)
            if not allow_reassign:
                self.warn('reassignment', node)
        self.set_scope(name, new_type)

    def visit_Name(self, node):
        print 'NAME:', node.id
        if node.id not in self.scope():
            self.warn('undefined', node)

    def visit_Module(self, node):
        self.new_scope(node)

    def visit_FunctionDef(self, node):
        scope = self.new_scope(node)
        self.set_scope(node.name, scope.get('__return__', 'None'))

    def visit_Return(self, node):
        self.check_assign(node, '__return__', node.value, allow_reassign=True)
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.check_assign(node, '__return__', Tuple(), allow_reassign=True)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets: # TODO: fix this
            self.check_assign(node, target.id, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign(node, node.target.id, node.value)
        self.generic_visit(node)

    def visit_Compare(self, node):
        nodes = [node.left] + node.comparators
        self.consistent_types(node, nodes)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.consistent_types(node, node.values)
        self.generic_visit(node)

    def visit_Delete(self, node):
        names = [target.id for target in node.targets]
        self.warn('delete', node)
        self.generic_visit(node)

    def visit_If(self, node):
        self.check_type(node.test, 'Bool', 'non-bool-if-condition')
        self.generic_visit(node)

    def visit_While(self, node):
        self.check_type(node.test, 'Bool', 'non-bool-while-condition')
        self.generic_visit(node)

    def visit_Slice(self, node):
        if node.lower is not None:
            self.check_type(node.lower, 'Num', 'non-num-slice')
        if node.upper is not None:
            self.check_type(node.upper, 'Num', 'non-num-slice')
        if node.step is not None:
            self.check_type(node.step, 'Num', 'non-num-slice')
        self.generic_visit(node)

    def visit_Index(self, node):
        self.check_type(node.value, 'Num', 'non-num-index')
        self.generic_visit(node)

    def visit_BinOp(self, node):
        self.check_type(node.left, 'Num', 'non-num-op')
        self.check_type(node.right, 'Num', 'non-num-op')
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        self.check_type(node.operand, 'Num', 'non-num-op')
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.check_type(node.test, 'Bool', 'non-bool-if-condition')
        self.consistent_types([node.body, node.orelse], 'if-else')
        self.generic_visit(node)


def main():
    filename = 'testcase.py'
    with open(filename) as test_case:
        source = test_case.read()
    tree = ast.parse(source, filename)
    visitor = Visitor()
    visitor.visit(tree)
    warnings = visitor.warnings()
    for warning in warnings:
        message = filename + ':{2} {0} "{1}"'.format(*warning[:3])
        print message + ' ({0})'.format(warning[3]) if warning[3] else message


if __name__ == '__main__':
    main()
