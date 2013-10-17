import ast
from imports import import_source
from expr import get_token, expression_type
from show import show_node
from context import Context


class Any():
    pass

class Tuple():
    pass


class Visitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)
        self._warnings = []
        self._context = Context()

    def namespace(self):
        return self._context.get_top_namespace()

    def warnings(self):
        return self._warnings

    def warn(self, category, node, details=None):
        self._warnings.append((category, show_node(node), node.lineno, details))

    def expr_type(self, node):
        return expression_type(node, self._context)

    def consistent_types(self, root_node, nodes):
        types = [self.expr_type(node) for node in nodes]
        # TODO: make another warning that allows nonetype
        if len(set(types)) > 1:
            details = ', '.join(types)
            self.warn('inconsitent-types', root_node, details)

    def check_type(self, node, typenames, category):
        if not isinstance(typenames, tuple):
            typenames = (typenames,)
        expr_typename = self.expr_type(node)
        if expr_typename not in typenames + ('Any',):
            self.warn(category, node)

    def check_assign(self, node, name, value, allow_reassign=False):
        new_type = self.expr_type(value)
        previous_type = self._context.get_type(name)
        if previous_type is not None:
            if previous_type != new_type:
                details = '{0} -> {1}'.format(previous_type, new_type)
                if previous_type == 'None' or new_type == 'None':
                    self.warn('maybe-type', node, details)
                else:
                    self.warn('type-change', node, details)
            if not allow_reassign:
                self.warn('reassignment', node)
        self._context.add_symbol(name, new_type)

    def visit_Name(self, node):
        if self._context.get_type(node.id) is None:
            self.warn('undefined', node)

    def visit_Module(self, node):
        self._context.begin_namespace()
        self.generic_visit(node)

    def visit_Import(self, node):
        import_visitor = Visitor()
        for alias in node.names:
            name = alias.name
            source = import_source(name)
            import_visitor.visit(ast.parse(source))
            namespace = import_visitor.namespace()
            self._context.add_symbol(name, name, namespace)

    def visit_ClassDef(self, node):
        self._context.begin_namespace()
        self.generic_visit(node)
        namespace = self._context.end_namespace()
        self._context.add_symbol(node.name, node.name, namespace)

    def visit_FunctionDef(self, node):
        self._context.begin_namespace()
        argnames = [arg.id for arg in node.args.args]
        for name in argnames:
            self._context.add_symbol(name, 'Any')
        if node.args.vararg is not None:
            self._context.add_symbol(node.args.vararg.id, 'Tuple')
        if node.args.kwarg is not None:
            self._context.add_symbol(node.args.kwarg.id, 'Dict')
        self.generic_visit(node)
        namespace = self._context.end_namespace()
        return_type = namespace.get_type('__return__') or 'None'
        self._context.add_symbol(node.name, return_type)

    def visit_Return(self, node):
        self.check_assign(node, '__return__', node.value, allow_reassign=True)
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.check_assign(node, '__return__', Tuple(), allow_reassign=True)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if get_token(target) in ('Tuple', 'List'):
                self.check_type(node.value, ('Tuple', 'List'), 'assign-type')
                if target.elts is not None:
                    for element in target.elts:
                        self.check_assign(element, element.id, Any())
            elif get_token(target) == 'Name':
                # Any type can be assigned to a name, so no type check
                self.check_assign(node, target.id, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign(node, node.target.id, node.value)
        self.generic_visit(node)

    def visit_Compare(self, node):
        self.consistent_types(node, [node.left] + node.comparators)
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

    print 'Namespace:'
    print visitor.namespace()


if __name__ == '__main__':
    main()
