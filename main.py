# pylint: disable=invalid-name
import sys
import os
import ast
from type_objects import Any, Num, List, Dict, Tuple, Instance, Class, \
    Function, NoneType, Bool, Str, Maybe
from imports import import_source
from expr import expression_type, call_argtypes, Arguments, get_assignments, \
    AssignError, make_argument_scope, get_token
from show import show_node
from context import Context, ExtendedContext


def first_type(types):
    for typ in types:
        if isinstance(typ, Maybe):
            return typ.subtype
        elif isinstance(typ, NoneType):
            continue
        return typ
    return NoneType


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


class FunctionEvaluator(object):
    def __init__(self, filepath, body_node, def_context):
        self.filepath = filepath
        self.body_node = body_node
        self.context = def_context
        self.cache = []
        self.recursion_block = False

    def __call__(self, argument_scope, clear_warnings=False):
        if self.recursion_block:
            return (Any(), [])
        for i, item in enumerate(self.cache):
            scope, result = item
            if scope == argument_scope:
                if clear_warnings:
                    self.cache[i] = (scope, (result[0], []))
                return result
        self.context.begin_scope()
        self.context.merge_scope(argument_scope)
        self.recursion_block = True
        visitor = Visitor(self.filepath, self.context)
        for stmt in self.body_node:
            visitor.visit(stmt)
        self.recursion_block = False
        warnings = visitor.warnings()
        scope = self.context.end_scope()
        return_type = scope.get('__return__', NoneType())
        result = (return_type, warnings)
        cache_result = (return_type, []) if clear_warnings else result
        self.cache.append((argument_scope, cache_result))
        return result


def builtin_context():
    filename = 'builtins.py'
    context = Context()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(this_dir, filename)) as builtins_file:
        source = builtins_file.read()
    _, _ = analyze(source, filename, context)
    return context


class Visitor(ast.NodeVisitor):
    def __init__(self, filepath='', context=None):
        ast.NodeVisitor.__init__(self)
        self._filepath = filepath
        self._warnings = []
        self._context = context if context is not None else builtin_context()

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
        return expression_type(node, ExtendedContext(self._context))

    def consistent_types(self, root_node, nodes, allow_maybe=False):
        types = [self.expr_type(node) for node in nodes]
        non_any_types = [x for x in types if not x == Any()]
        base_type = first_type(non_any_types)
        options = ([base_type, Maybe(base_type), NoneType()]
                    if allow_maybe else [base_type])
        for typ in non_any_types:
            if not any(typ == x for x in options):
                details = ', '.join([str(x) for x in types])
                self.warn('inconsitent-types', root_node, details)
                return

    def check_type(self, node, types, category):
        if not isinstance(types, tuple):
            types = (types,)
        expr_type = self.expr_type(node)
        if expr_type not in types + (Any(),):
            self.warn(category, node)

    def check_return(self, node, return_type):
        name = '__return__'
        previous_type = self._context.get_type(name)
        if previous_type is None:
            self._context.add_symbol(name, return_type)
            return
        details = '{0} -> {1}'.format(previous_type, return_type)
        if isinstance(return_type, NoneType):
            if not isinstance(previous_type, (NoneType, Maybe)):
                self._context.add_symbol(name, Maybe(previous_type))
        elif isinstance(return_type, Maybe):
            if not isinstance(previous_type, NoneType):
                if return_type != previous_type:
                    self.warn('type-change', node, details)
        else:
            if isinstance(previous_type, NoneType):
                self._context.add_symbol(name, Maybe(return_type))
            elif isinstance(previous_type, Maybe):
                if return_type != previous_type.subtype:
                    self.warn('type-change', node, details)
            elif return_type != previous_type:
                self.warn('type-change', node, details)

    def check_assign_name_type(self, node, name, new_type):
        previous_type = self._context.get_type(name)
        if previous_type is not None:
            if previous_type != new_type:
                details = '{0} -> {1}'.format(previous_type, new_type)
                self.warn('type-change', node, details)
            self.warn('reassignment', node)
        self._context.add_symbol(name, new_type)

    def check_assign_name(self, node, name, value):
        value_type = self.expr_type(value)
        self.check_assign_name_type(node, name, value_type)

    def check_assign(self, node, target, value, generator=False):
        try:
            assignments = get_assignments(target, value,
                ExtendedContext(self._context), generator=generator)
        except AssignError:
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
        # don't end scope so that caller can see what is in the scope

    def visit_Import(self, node):
        source_dir = os.path.abspath(os.path.dirname(self._filepath))
        for alias in node.names:
            name = alias.name
            source, filepath = import_source(name, [source_dir])
            _, scope = analyze(source, filepath)    # ignore warnings
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
        arguments = Arguments(node.args, ExtendedContext(self._context),
            node.decorator_list)
        specified_types = zip(arguments.names,
            arguments.explicit_types, arguments.default_types)
        for name, explicit_type, default_type in specified_types:
            if (explicit_type != Any() and default_type != Any() and
                    default_type != explicit_type):
                self.warn('default-argument-type-error', node, name)
        return_type = FunctionEvaluator(self._filepath, node.body,
            self._context.copy())
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
        if not isinstance(func_type, Function):
            return self.warn('not-a-function', node, node.func.id)

        argtypes, kwargtypes = call_argtypes(node,
            ExtendedContext(self._context))
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

        # Add warnings from function body (probably already cached)
        if isinstance(func_type, Function): # skip class constructors
            argument_scope = make_argument_scope(node, func_type.arguments,
                ExtendedContext(self._context))
            return_type, warnings = func_type.return_type(argument_scope, True)
            self._warnings.extend(warnings)

        self.generic_visit(node)

    def visit_Return(self, node):
        return_type = self.expr_type(node.value)
        self.check_return(node, return_type)
        self.generic_visit(node)

    def visit_Yield(self, node):
        yield_type = self.expr_type(node).item_type
        self.check_return(node, yield_type)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self.check_assign(node, target, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign(node, node.target, node.value)
        self.generic_visit(node)

    def visit_Compare(self, node):
        if any(get_token(op) in ['In', 'NotIn'] for op in node.ops):
            if len(node.ops) > 1 or len(node.comparators) > 1:
                self.warn('in-operator-chaining', node)
            else:
                rhs_type = self.expr_type(node.comparators[0])
                if isinstance(rhs_type, List):
                    self.consistent_types(node,
                        [node.left, rhs_type.item_type])
                elif isinstance(rhs_type, Dict):
                    self.consistent_types(node, [node.left, rhs_type.key_type])
                else:
                    self.warn('in-operator-argument-not-list-or-dict', node)
        else:
            self.consistent_types(node, [node.left] + node.comparators)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.consistent_types(node, node.values)
        self.generic_visit(node)

    def visit_Delete(self, node):
        # TODO: need to support identifiers, dict items, attributes, list items
        #names = [target.id for target in node.targets]
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
        # index can mean list index or dict lookup, so could be any type
        self.generic_visit(node)

    def visit_BinOp(self, node):
        operator = get_token(node.op)
        types = {self.expr_type(node.left), self.expr_type(node.right)}
        if operator == 'Mult':
            if types != {Num()} and types != {Num(), Str()}:
                self.warn('invalid-types', node)
        elif operator == 'Add':
            if len(types) > 1:
                if not all(isinstance(x, Tuple) for x in types):
                    self.warn('inconsistent-types', node)
            elif not isinstance(iter(types).next(), (Num, Str, List, Tuple)):
                self.warn('invalid-type', node)
        else:
            self.check_type(node.left, Num(), 'non-num-operand')
            self.check_type(node.right, Num(), 'non-num-operand')
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        operator = get_token(node.op)
        if operator == 'Not':
            self.check_type(node.operand, Bool(), 'non-bool-operand')
        else:
            self.check_type(node.operand, Num(), 'non-num-operand')
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.check_type(node.test, Bool(), 'non-bool-if-condition')
        self.consistent_types(node, [node.body, node.orelse], allow_maybe=True)
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

    def visit_List(self, node):
        self.consistent_types(node, node.elts)

    def visit_Dict(self, node):
        self.consistent_types(node, node.keys)
        self.consistent_types(node, node.values)

    def visit_Set(self, node):
        self.consistent_types(node, node.elts)


def dump_scope(scope):
    end = '\n' if scope else ''
    return '\n'.join([name + ' ' + str(scope[name])
        for name in sorted(scope.keys())]) + end


def analyze(source, filepath=None, context=None):
    tree = ast.parse(source, filepath)
    visitor = Visitor(filepath, context)
    visitor.visit(tree)
    return visitor.warnings(), visitor.scope()


def analysis(source, filepath=None):
    warnings, scope = analyze(source, filepath)
    warning_output = ''.join([str(warning) + '\n' for warning in warnings])
    scope_output = dump_scope(scope)
    separator = '\n' if warning_output and scope_output else ''
    return scope_output + separator + warning_output


def main():
    filepath = sys.argv[1]
    with open(filepath) as source_file:
        source = source_file.read()
    sys.stdout.write(analysis(source, filepath))


if __name__ == '__main__':
    main()
