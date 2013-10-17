import ast


class Any():
    pass

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
        return dump(node.targets[0]) + ' = ...'
    if token == 'AugAssign':
        return dump(node.target) + ' = ...'
    if token == 'Compare':
        return ' '.join([get_token(op) for op in node.ops])
    return token


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


# Tricky: need to support obj1.obj2.x where obj2 is an instance
# of a class that may not be defined in the current scope
# Idea: maintain a separate scope dict that contains all the class
# type data, keyed by classname
# Assume that all attributes are either set in __init__ or method names

# Also, if we import one function from another module, and that function
# calls another function that was not imported, we need to know the type
# of the other function without having it in our scope. Perhaps we should
# maintain two scopes. One for everything that is loaded, another for
# everything that is in scope. LoadScope vs. NameScope
# Whenever you add to LoadScope, it automatically adds to NameScope,
# but not the other way around.

# import statement creates a whole new scope heirarchy, not just a new level

# type check Attribute(expr, attr):
# classname = expr_type(expr)
# typename = scope.getattr(classname, attr) # 
class Namespace(object):
    def __init__(self):
        self._levels = []

    def add_name(self, name, typename):
        self._levels[-1][name] = typename

    def gettype(self, name):
        for level in reversed(self._levels):
            if name in level:
                return level[name]
        return None

    def getattr(self, classname, attr, default=None):
        pass

    def push_scope(self, scope={}):
        self._levels.append(scope)

    def pop_scope(self):
        return self._levels.pop()



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
        if node.id not in self.scope():
            self.warn('undefined', node)

    def visit_Module(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        self._scopes.pop()

    def visit_Import(self, node):
        import_visitor = Visitor()
        for alias in node.names:

    def visit_Class(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        scope = self._scopes.pop()
        #self.set_scope(class.name, scope)
        self.set_scope(class.name, class.name)
        self.set_subscope(class.name, scope)

    def visit_FunctionDef(self, node):
        argnames = [arg.id for arg in node.args.args]
        argscope = {name: 'Any' for name in argnames}
        if node.args.vararg is not None:
            argscope[node.args.vararg.id] = 'Tuple'
        if node.args.kwarg is not None:
            argscope[node.args.kwarg.id] = 'Dict'
        self._scopes.append(argscope)
        self.generic_visit(node)
        scope = self._scopes.pop()
        self.set_scope(node.name, scope.get('__return__', 'None'))

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


if __name__ == '__main__':
    main()
