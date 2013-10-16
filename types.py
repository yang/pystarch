import ast, _ast


class Visitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)
        self._warnings = []
        self._scopes = []

    def warnings(self):
        return self._warnings

    def warn(self, category, what, lineno):
        self._warnings.append((category, what, lineno))

    def set_scope(self, name, value):
        self._scopes[-1][name] = value

    def scope(self, name):
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def get_type(self, node):
        typename = node.__class__.__name__
        if typename == 'Name':
            return self.scope(node.id)
        return typename

    def visit_scope(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        print self._scopes[-1]
        self._scopes.pop()

    def visit_Module(self, node):
        self.visit_scope(node)

    def visit_FunctionDef(self, node):
        self.visit_scope(node)

    def visit_Compare(self, node):
        nodes = [node.left] + node.comparators
        types = [self.get_type(node) for node in nodes]
        if len(set(types)) > 1:
            self.warn('inconsitent-types', 'comparison', node.lineno)

    def visit_Assign(self, node):
        new_type = node.value.__class__.__name__
        for target in node.targets:
            name = target.id
            previous_type = self.scope(name)
            if previous_type is not None:
                if previous_type != new_type:
                    self.warn('type-change', name, node.lineno)
                self.warn('reassignment', name, node.lineno)
            self.set_scope(name, new_type)


def main():
    filename = 'testcase.py'
    with open(filename) as test_case:
        source = test_case.read()
    tree = ast.parse(source, filename)
    visitor = Visitor()
    visitor.visit(tree)
    warnings = visitor.warnings()
    for warning in warnings:
        print '{0} of {1} on line {2}'.format(*warning)

if __name__ == '__main__':
    main()
