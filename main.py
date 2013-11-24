import sys
import os
import ast
from imports import import_source
from expr import get_token, expression_type
from show import show_node
from context import Context


class Any():
    pass

class Tuple():
    pass


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


# args parameter is a list of 2-tuples of the form (name, typename)
# minargs is the minimum number of positional arguments that must be passed
class Arguments(object):
    def __init__(self, args, vararg_name, kwarg_name, minargs):
        self._args = args
        self.argnames = [arg[0] for arg in args]
        self.argtypes = [arg[1] for arg in args]
        self.kwargtypes = {arg[0]: arg[1] for arg in args if arg[1]}
        self.vararg_name = vararg_name
        self.kwarg_name = kwarg_name
        self.minargs = minargs

    def __str__(self):
        vararg = (', {0}: Tuple'.format(self.vararg_name)
            if self.vararg_name else '')
        kwarg = (', {0}: Dict'.format(self.kwarg_name)
            if self.kwarg_name else '')
        return (', '.join(arg[0] + ': ' + arg[1] for arg in self._args)
            + vararg + kwarg)


class Visitor(ast.NodeVisitor):
    def __init__(self, filepath):
        ast.NodeVisitor.__init__(self)
        self._filepath = filepath
        self._warnings = []
        self._context = Context()

    def namespace(self):
        return self._context.get_top_namespace()

    def begin_namespace(self):
        self._context.begin_namespace()

    def end_namespace(self):
        return self._context.end_namespace()

    def warnings(self):
        return self._warnings

    def warn(self, category, node, details=None):
        warning = NodeWarning(self._filepath, category, node, details)
        self._warnings.append(warning)

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

    def check_assign_name(self, node, name, value, allow_reassign=False,
            allow_none_conversion=False):
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
            if allow_none_conversion and new_type == 'None':
                return      # don't override non-none with none
        self._context.add_symbol(name, new_type)

    def check_assign(self, node, target, value):
        if get_token(target) in ('Tuple', 'List'):
            self.check_type(value, ('Tuple', 'List'), 'assign-type')
            if target.elts is not None:
                for element in target.elts:
                    self.check_assign_name(element, element.id, Any())
        elif get_token(target) == 'Name':
            # Any type can be assigned to a name, so no type check
            self.check_assign_name(node, target.id, value)

    def argtypes(self, call_node):
        types = []
        keyword_types = {}
        for arg in call_node.args:
            types.append(self.expr_type(arg))
        for keyword in call_node.keywords:
            keyword_types[keyword.arg] = self.expr_type(keyword.value)
        if call_node.starargs is not None:
            keyword_types['*args'] = self.expr_type(call_node.starargs)
        if call_node.kwargs is not None:
            keyword_types['**kwargs'] = self.expr_type(call_node.kwargs)
        return types, keyword_types

    def visit_Name(self, node):
        if self._context.get_type(node.id) is None:
            self.warn('undefined', node)

    def visit_Module(self, node):
        self.begin_namespace()
        self.generic_visit(node)

    def visit_Import(self, node):
        source_dir = os.path.abspath(os.path.dirname(self._filepath))
        for alias in node.names:
            name = alias.name
            source, filepath = import_source(name, [source_dir])
            import_visitor = Visitor(filepath)
            import_visitor.visit(ast.parse(source))
            namespace = import_visitor.namespace()
            self._context.add_symbol(name, name, None, namespace)

    def visit_ClassDef(self, node):
        self.begin_namespace()
        self.generic_visit(node)
        namespace = self.end_namespace()
        # TODO: get __init__ args
        # TODO: save self.x into namespace where "self" is 1st param to init
        self._context.add_symbol(node.name, node.name, None, namespace)

    def visit_FunctionDef(self, node):
        self.begin_namespace()
        argnames = [arg.id for arg in node.args.args]
        minargs = len(node.args.args) - len(node.args.defaults)
        argtypes = (['Any'] * minargs) + [self.expr_type(d) for d in
            node.args.defaults]
        arguments = Arguments(zip(argnames, argtypes), node.args.vararg,
            node.args.kwarg, minargs)
        for decorator in node.decorator_list:
            if get_token(decorator) == 'Call':
                if show_node(decorator.func) == 'types':
                    argtypes, kwargtypes = self.argtypes(decorator)
        for i, name in enumerate(argnames):
            # TODO: add support for Python3 annotations here
            self._context.add_symbol(name, 'Any')
        if node.args.vararg is not None:
            self._context.add_symbol(node.args.vararg, 'Tuple')
        if node.args.kwarg is not None:
            self._context.add_symbol(node.args.kwarg, 'Dict')
        self.generic_visit(node)
        namespace = self.end_namespace()
        return_type = namespace.get_type('__return__') or 'None'
        self._context.add_symbol(node.name, return_type, arguments)

    def type_error(self, node, label, got, expected):
        template = '{0} expected type {1} but got {2}'
        details = template.format(label, ' or '.join(expected), got)
        self.warn('type-error', node, details)

    def check_argument_type(self, node, label, got, expected):
        assert isinstance(expected, list)
        if 'Any' not in expected and got not in expected + ['None']:
            self.type_error(node, 'Argument ' + label, got, expected)

    def visit_Call(self, node):
        if not hasattr(node.func, 'id'):
            return      # TODO: support class attributes
        symbol = self._context.get_symbol(node.func.id)
        if not symbol:
            return self.warn('undefined-function', node, node.func.id)
        if not symbol.arguments:
            return self.warn('not-a-function', node, node.func)
        argtypes, kwargtypes = self.argtypes(node)
        # make sure all required arguments are specified
        minargs = symbol.arguments.minargs
        required_kwargs = symbol.arguments.argnames[len(argtypes):minargs]
        missing = [name for name in required_kwargs if name not in kwargtypes]
        for missing_argument in missing:
            self.warn('missing-argument', node, missing_argument)
        if symbol.arguments.vararg_name is None:
            if len(argtypes) > len(symbol.arguments.argtypes):
                self.warn('too-many-arguments', node)
        for i, argtype in enumerate(argtypes[:len(symbol.arguments.argtypes)]):
            deftype = symbol.arguments.argtypes[i]
            self.check_argument_type(node, i + 1, argtype, [deftype])
        for name, kwargtype in kwargtypes.items():
            if name == '*args' and kwargtype not in ['Tuple', 'List']:
                self.check_argument_type(node, name, kwargtype,
                    ['Tuple', 'List'])
            elif name == '**kwargs':
                self.check_argument_type(node, name, kwargtype, ['Dict'])
            else:
                deftype = symbol.arguments.kwargtypes.get(name)
                if deftype is None:
                    self.warn('extra-keyword', node, name)
                else:
                    self.check_argument_type(node, name, kwargtype, [deftype])
        self.generic_visit(node)

    def visit_Return(self, node):
        self.check_assign_name(node, '__return__', node.value,
            allow_reassign=True, allow_none_conversion=True)
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.check_assign_name(node, '__return__', Tuple(),
            allow_reassign=True, allow_none_conversion=True)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self.check_assign(node, target, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign_name(node, node.target.id, node.value)
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

    def visit_For(self, node):
        # Python doesn't create a namespace for "for", but we will 
        # treat it as if it did because it should
        self.begin_namespace()
        # TODO: support getting the type of the items of an iterator
        # so we can replace Any() with the type of the iterator
        self.check_assign(node, node.target, Any())
        self.generic_visit(node)
        self.end_namespace()

    def visit_With(self, node):
        self.begin_namespace()
        if node.optional_vars:
            self.check_assign(node, node.optional_vars, node.context_expr)
        self.generic_visit(node)
        self.end_namespace()


def analyze(source, filepath=None):
    tree = ast.parse(source, filepath)
    visitor = Visitor(filepath)
    visitor.visit(tree)
    print(visitor.namespace())
    return visitor.warnings()


def analysis(source, filepath=None):
    warnings = analyze(source, filepath)
    return ''.join([str(warning) + '\n' for warning in warnings])


def main():
    filepath = sys.argv[1]
    with open(filepath) as source_file:
        source = source_file.read()
    output = analysis(source, filepath)
    sys.stdout.write(analysis(source, filepath))


if __name__ == '__main__':
    main()
