import sys
import os
import ast
from type_objects import Any, Num, Str, List, Dict, Tuple, Instance, Class, \
    Function, NoneType, Bool
from imports import import_source
from expr import get_token, expression_type, call_argtypes, Arguments, \
    get_assignments
from show import show_node
from context import Context


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


class Visitor(ast.NodeVisitor):
    def __init__(self, filepath):
        ast.NodeVisitor.__init__(self)
        self._filepath = filepath
        self._warnings = []
        self._context = Context()

    def scope(self):
        return self._context.get_top_scope()

    def begin_scope(self):
        self._context.begin_scope()

    def end_scope(self):
        return self._context.end_scope()

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
            details = ', '.join([str(x) for x in types])
            self.warn('inconsitent-types', root_node, details)

    def check_type(self, node, types, category):
        if not isinstance(types, tuple):
            types = (types,)
        expr_type = self.expr_type(node)
        if expr_type not in types + (Any(),):
            self.warn(category, node)

    def check_assign_name_type(self, node, name, new_type,
            allow_reassign=False, allow_none_conversion=False):
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

    def check_assign_name(self, node, name, value, allow_reassign=False,
            allow_none_conversion=False):
        value_type = self.expr_type(value)
        self.check_assign_name_type(node, name, value_type,
            allow_reassign=allow_reassign,
            allow_none_conversion=allow_none_conversion)

    def check_assign(self, node, target, value, generator=False):
        try:
            assignments = get_assignments(target, value, self._context,
                generator=generator)
        except (TypeError, ValueError):
            self.warn('assignment-error', node)
            return
        for name, assigned_type in assignments:
            self.check_assign_name_type(node, name, assigned_type)

    def visit_Name(self, node):
        if self._context.get_type(node.id) is None:
            self.warn('undefined', node)

    def visit_Module(self, node):
        self.begin_scope()
        self.generic_visit(node)

    def visit_Import(self, node):
        source_dir = os.path.abspath(os.path.dirname(self._filepath))
        for alias in node.names:
            name = alias.name
            source, filepath = import_source(name, [source_dir])
            import_visitor = Visitor(filepath)
            import_visitor.visit(ast.parse(source))
            scope = import_visitor.scope()
            import_type = Instance('__import__', scope)
            self._context.add_symbol(name, import_type)

    def visit_ClassDef(self, node):
        self.begin_scope()
        self.generic_visit(node)
        scope = self.end_scope()
        # TODO: handle case of no __init__ function
        if '__init__' in scope:
            init_arguments = scope['__init__'].arguments
            arguments = Arguments.copy_without_first_argument(init_arguments)
        else:
            arguments = Arguments()
        return_type = Instance(node.name, scope)
        # TODO: separate class/static methods and attributes from the rest
        class_type = Class(arguments, return_type, {})
        # TODO: save self.x into scope where "self" is 1st param to init
        self._context.add_symbol(node.name, class_type)

    def visit_FunctionDef(self, node):
        arguments = Arguments(node.args, self._context, node.decorator_list)
        specified_types = zip(arguments.names,
            arguments.explicit_types, arguments.default_types)
        for name, explicit_type, default_type in specified_types:
            if (explicit_type != Any() and default_type != Any() and
                    default_type != explicit_type):
                self.warn('default-argument-type-error', node, name)
        self.begin_scope()
        arguments.load_context(self._context)
        self.generic_visit(node)
        scope = self.end_scope()
        return_type = scope.get('__return__', NoneType())
        function_type = Function(arguments, return_type)
        self._context.add_symbol(node.name, function_type)

    def type_error(self, node, label, got, expected):
        template = '{0} expected type {1} but got {2}'
        expected_str = [str(x) for x in expected]
        details = template.format(label, ' or '.join(expected_str), str(got))
        self.warn('type-error', node, details)

    def check_argument_type(self, node, label, got, expected):
        assert isinstance(expected, list)
        if Any() not in expected and got not in expected + [NoneType()]:
            self.type_error(node, 'Argument ' + label, got, expected)

    def visit_Call(self, node):
        if not hasattr(node.func, 'id'):
            return      # TODO: support class attributes
        func_type = self._context.get_type(node.func.id)
        if not func_type:
            return self.warn('undefined-function', node, node.func.id)
        if not func_type.arguments:
            return self.warn('not-a-function', node, node.func.id)
        argtypes, kwargtypes = call_argtypes(node, self._context)
        # make sure all required arguments are specified
        minargs = func_type.arguments.min_count
        required_kwargs = func_type.arguments.names[len(argtypes):minargs]
        missing = [name for name in required_kwargs if name not in kwargtypes]
        for missing_argument in missing:
            self.warn('missing-argument', node, missing_argument)
        if func_type.arguments.vararg_name is None:
            if len(argtypes) > len(func_type.arguments.types):
                self.warn('too-many-arguments', node)
        for i, argtype in enumerate(argtypes[:len(func_type.arguments.types)]):
            deftype = func_type.arguments.types[i]
            self.check_argument_type(node, i + 1, argtype, [deftype])
        for name, kwargtype in kwargtypes.items():
            if name == '*args':
                if not isinstance(kwargtype, (Tuple, List)):
                    self.warn('invlaid-vararg-type', node)
            elif name == '**kwargs':
                if not isinstance(kwargtype, Dict):
                    self.warn('invalid-kwarg-type', node)
            else:
                deftype = func_type.arguments.get_dict().get(name)
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
        yield_type = self.expr_type(node).item_type
        self.check_assign_name_type(node, '__return__', yield_type,
            allow_reassign=True, allow_none_conversion=True)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self.check_assign(node, target, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign(node, node.target, node.value)
        self.generic_visit(node)

    def visit_Compare(self, node):
        self.consistent_types(node, [node.left] + node.comparators)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.consistent_types(node, node.values)
        self.generic_visit(node)

    def visit_Delete(self, node):
        # TODO: need to support identifiers, dict items, attributes, list items
        names = [target.id for target in node.targets]
        self.warn('delete', node)
        self.generic_visit(node)

    def visit_If(self, node):
        self.check_type(node.test, Bool(), 'non-bool-if-condition')
        self.generic_visit(node)

    def visit_While(self, node):
        self.check_type(node.test, Bool(), 'non-bool-while-condition')
        self.generic_visit(node)

    def visit_Slice(self, node):
        if node.lower is not None:
            self.check_type(node.lower, Num(), 'non-num-slice')
        if node.upper is not None:
            self.check_type(node.upper, Num(), 'non-num-slice')
        if node.step is not None:
            self.check_type(node.step, Num(), 'non-num-slice')
        self.generic_visit(node)

    def visit_Index(self, node):
        self.check_type(node.value, Num(), 'non-num-index')
        self.generic_visit(node)

    def visit_BinOp(self, node):
        # TODO: allow Num and Str with '*'
        self.check_type(node.left, Num(), 'non-num-op')
        self.check_type(node.right, Num(), 'non-num-op')
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        # TODO: Bool() type for "not" operator
        self.check_type(node.operand, Num(), 'non-num-op')
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.check_type(node.test, Bool(), 'non-bool-if-condition')
        self.consistent_types([node.body, node.orelse], 'if-else')
        self.generic_visit(node)

    def visit_For(self, node):
        # Python doesn't create a scope for "for", but we will 
        # treat it as if it did because it should
        self.begin_scope()
        self.check_assign(node, node.target, node.iter, generator=True)
        self.generic_visit(node)
        self.end_scope()

    def visit_With(self, node):
        self.begin_scope()
        if node.optional_vars:
            self.check_assign(node, node.optional_vars, node.context_expr)
        self.generic_visit(node)
        self.end_scope()


def analyze(source, filepath=None):
    tree = ast.parse(source, filepath)
    visitor = Visitor(filepath)
    visitor.visit(tree)
    #print(visitor.scope())
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
