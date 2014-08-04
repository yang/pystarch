# pylint: disable=invalid-name
import sys
import os
import ast
import cPickle as pickle
from hashlib import sha256
from imports import import_source
from warning import NodeWarning
from backend import expression_type, call_argtypes, Arguments, \
    get_assignments, make_argument_scope, get_token, assign_generators, \
    unify_types, known_types, Context, ExtendedContext, Scope, \
    static_evaluate, UnknownValue, NoneType, Bool, Num, Str, List, Dict, \
    Tuple, Instance, Class, Function, Maybe, Unknown, comparable_types, \
    type_set_match, maybe_inferences, unifiable_types


NAME = 'strictpy'
__version__ = '1.0.0'


def builtin_context():
    filename = 'builtins.py'
    context = Context()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(this_dir, filename)) as builtins_file:
        source = builtins_file.read()
    analyze(source, filename, context)
    return context


def import_module(name, current_filepath, imported):
    source, filepath, is_package = import_source(name, current_filepath)
    cache_filename = sha256(filepath + '~' + source).hexdigest()
    cache_filepath = os.path.join(os.sep, 'var', 'cache', NAME,
                                  __version__, cache_filename)

    if os.path.exists(cache_filepath):
        with open(cache_filepath, 'rb') as cache_file:
            return pickle.load(cache_file), filepath, is_package
    elif filepath in imported:
        i = imported.index(filepath)
        paths = ' -> '.join(imported[i:] + [filepath])
        #print('CIRCULAR: ' + paths)
        return Instance('object', Scope()), filepath, is_package
    else:
        imported.append(filepath)
        scope, _, _ = analyze(source, filepath, imported=imported)
        module = Instance('object', scope)
        with open(cache_filepath, 'wb') as cache_file:
            pickle.dump(module, cache_file, pickle.HIGHEST_PROTOCOL)
        return module, filepath, is_package


def import_chain(fully_qualified_name, asname, import_scope, current_filepath,
        imported):
    scope = import_scope
    filepath = current_filepath
    is_package = True
    names = fully_qualified_name.split('.') if fully_qualified_name else [None]
    for name in names:
        if scope is None:
            raise RuntimeError('Cannot import ' + fully_qualified_name)
        if is_package:
            import_type, filepath, is_package = import_module(
                name, filepath, imported)
            if asname is None:
                scope.add_symbol(name, import_type)
            scope = import_type.attributes
        else:
            import_type = scope.get_type(name)
            scope = None
    if asname is not None:
        import_scope.add_symbol(asname, import_type)
    return import_type


def get_path_for_level(filepath, level):
    for _ in range(level):
        filepath = os.path.dirname(filepath)
    if level > 0:
        filepath = os.path.join(filepath, '__init__.py')
    return filepath


# only for "from x import y" syntax
def import_from_chain(fully_qualified_name, level, current_filepath, imported):
    return import_chain(fully_qualified_name, None, Scope(),
        get_path_for_level(current_filepath, level), imported)


class FunctionEvaluator(object):
    def __init__(self, filepath, body_node, def_context):
        self.filepath = filepath
        self.body_node = body_node
        self.context = def_context
        self.cache = []
        self.recursion_block = False

    def evaluate(self, argument_scope, clear_warnings=False):
        if self.recursion_block:
            return Unknown(), [], []
        self.context.begin_scope()
        self.context.merge_scope(argument_scope)
        self.recursion_block = True
        visitor = Visitor(self.filepath, self.context)
        for stmt in self.body_node:
            visitor.visit(stmt)
        self.recursion_block = False
        _, warnings, annotations = visitor.report()
        scope = self.context.end_scope()
        return_type = scope.get_return_type() or NoneType()
        return return_type, warnings, annotations

    def __call__(self, argument_scope, clear_warnings=False):
        for i, item in enumerate(self.cache):
            cache_argument_scope, result = item
            if cache_argument_scope == argument_scope:
                if clear_warnings:
                    return_type, _, _ = result
                    cache_result = return_type, [], annotations
                    self.cache[i] = (cache_argument_scope, cache_result)
                return result
        result = self.evaluate(argument_scope, clear_warnings)
        cache_result = ((result[0], [], result[2])
                         if clear_warnings else result)
        self.cache.append((argument_scope, cache_result))
        return result


class Visitor(ast.NodeVisitor):
    def __init__(self, filepath='', context=None, imported=[]):
        ast.NodeVisitor.__init__(self)
        self._filepath = filepath
        self._warnings = []
        self._context = context if context is not None else builtin_context()
        self._imported = imported
        self._annotations = []

    def scope(self):
        return self._context.get_top_scope()

    def warnings(self):
        return self._warnings

    def annotations(self):
        return self._annotations

    def report(self):
        return self.scope(), self.warnings(), self.annotations()

    def begin_scope(self):
        self._context.begin_scope()

    def end_scope(self):
        return self._context.end_scope()

    def warn(self, category, node, details=None):
        warning = NodeWarning(self._filepath, category, node, details)
        self._warnings.append(warning)

    def expr_type(self, node):
        return expression_type(node, ExtendedContext(self._context))

    def evaluate(self, node):
        return static_evaluate(node, ExtendedContext(self._context))

    def consistent_types(self, check_func, root_node, nodes):
        types = [self.expr_type(node) for node in nodes]
        if not check_func(types):
            details = ', '.join([str(x) for x in types])
            self.warn('inconsistent-types', root_node, details)

    def check_type(self, node, types, override=None):
        if not isinstance(types, tuple):
            types = (types,)
        expr_type = override if override is not None else self.expr_type(node)
        if not any(isinstance(expr_type, x) for x in types + (Unknown,)):
            options = ' or '.join([x.__name__ for x in types])
            details = '{0} vs {1}'.format(expr_type, options)
            self.warn('type-error', node, details)

    def check_type_set(self, node, types, type_sets):
        if not isinstance(type_sets, tuple):
            type_sets = (type_sets,)
        if not any(type_set_match(types, x) for x in type_sets):
            got = ', '.join([str(x) for x in types])
            fmt_set = lambda s: '{' + ', '.join(x.__name__
                for x in sorted(s)) + '}'
            options = ' or '.join([fmt_set(x) for x in type_sets])
            details = '[{0}] vs {1}'.format(got, options)
            self.warn('type-error', node, details)

    def check_return(self, node, is_yield=False):
        value_type = self.expr_type(node.value)
        return_type = List(value_type) if is_yield else value_type
        static_value = self.evaluate(node.value)
        previous_type = self._context.get_return_type()
        if previous_type is None:
            self._context.set_return(return_type, static_value)
            return
        new_type = unify_types([previous_type, return_type])
        if new_type == Unknown():
            details = '{0} -> {1}'.format(previous_type, return_type)
            self.warn('multiple-return-types', node, details)
        else:
            self._context.set_return(new_type, static_value)

    def check_assign_name_type(self, node, name, new_type, static_value):
        previous_type = self._context.get_type(name)
        if previous_type is not None:
            if previous_type != new_type:
                details = '{0} -> {1}'.format(previous_type, new_type)
                self.warn('type-change', node, details)
            self.warn('reassignment', node)
        self._context.add_symbol(name, new_type, static_value)

    def check_assign(self, node, target, value, generator=False):
        assignments = get_assignments(target, value,
            ExtendedContext(self._context), generator=generator)
        for name, assigned_type, static_value in assignments:
            self.check_assign_name_type(node, name, assigned_type,
                                        static_value)

    def visit_Name(self, node):
        the_type = self._context.get_type(node.id)
        if the_type is None:
            self.warn('undefined', node)
        if not isinstance(the_type, Unknown):
            label = str(the_type) if the_type else None
            annotation = (self._filepath, node.lineno, node.col_offset,
                          node.id, label)
            self._annotations.append(annotation)

    def visit_Module(self, node):
        self.begin_scope()
        self.generic_visit(node)
        # don't end scope so that caller can see what is in the scope

    def visit_Import(self, node):
        scope = self._context.get_top_scope()
        for alias in node.names:
            try:
                import_chain(alias.name, alias.asname, scope, self._filepath,
                    self._imported)
            except RuntimeError as failure:
                self.warn('import-failed', node,
                          alias.name + ': ' + str(failure))

    def visit_ImportFrom(self, node):
        try:
            module = import_from_chain(node.module, node.level, self._filepath,
                self._imported)
        except RuntimeError as failure:
            self.warn('import-failed', node, '{0}: {1}'.format(
                node.module, failure))
            return
        if not isinstance(module, Instance):
            self.warn('invalid-import', node, node.module)
            return

        for alias in node.names:
            symbol_name = alias.asname or alias.name
            symbol_type = module.attributes.get_type(alias.name)
            self._context.add_symbol(symbol_name, symbol_type)

    def visit_ClassDef(self, node):
        self.begin_scope()
        self.generic_visit(node)
        scope = self.end_scope()
        # TODO: handle case of no __init__ function
        if '__init__' in scope:
            init_arguments = scope.get_type('__init__').arguments
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
            if (explicit_type != Unknown() and default_type != Unknown() and
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
        if Unknown() not in expected and got not in expected + [NoneType()]:
            self.type_error(node, 'Argument ' + str(label), got, expected)

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
            _, warnings, annotations = func_type.return_type(
                argument_scope, True)
            self._annotations.extend(annotations)
            self._warnings.extend(warnings)

        self.generic_visit(node)

    def visit_Return(self, node):
        self.check_return(node)
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.check_return(node, is_yield=True)
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
                    self.consistent_types(comparable_types, node,
                                          [node.left, rhs_type.item_type])
                elif isinstance(rhs_type, Dict):
                    self.consistent_types(comparable_types, node,
                                          [node.left, rhs_type.key_type])
                elif not isinstance(rhs_type, Unknown):
                    self.warn('in-operator-argument-not-list-or-dict', node)
        elif any(get_token(op) in ['Is', 'IsNot'] for op in node.ops):
            if len(node.ops) > 1 or len(node.comparators) > 1:
                self.warn('is-operator-chaining', node)
            else:
                rhs = node.comparators[0]
                lhs_type = self.expr_type(node.left)
                rhs_type = self.expr_type(rhs)
                if not (isinstance(lhs_type, Maybe)
                        and isinstance(rhs_type, NoneType)):
                    self.consistent_types(comparable_types, node,
                                          [node.left, rhs])
        else:
            self.consistent_types(comparable_types, node,
                                  [node.left] + node.comparators)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        for value in node.values:
            self.check_type(value, Bool)
        self.generic_visit(node)

    def visit_Delete(self, node):
        # TODO: need to support identifiers, dict items, attributes, list items
        #names = [target.id for target in node.targets]
        self.warn('delete', node)
        self.generic_visit(node)

    def visit_If(self, node):
        self.visit(node.test)
        self.check_type(node.test, Bool)
        test_value = static_evaluate(node.test, ExtendedContext(self._context))
        if not isinstance(test_value, UnknownValue):
            self.warn('constant-if-condition', node)

        ext_ctx = ExtendedContext(self._context)
        if_inferences, else_inferences = maybe_inferences(node.test, ext_ctx)

        self.begin_scope()
        self._context.apply_type_inferences(if_inferences)
        for stmt in node.body:
            self.visit(stmt)
        if_scope = self.end_scope()

        if node.orelse:
            self.begin_scope()
            self._context.apply_type_inferences(else_inferences)
            for stmt in node.orelse:
                self.visit(stmt)
            else_scope = self.end_scope()
        else:
            else_scope = Scope()

        diffs = set(if_scope.names()) ^ set(else_scope.names())
        for diff in diffs:
            if diff not in self._context:
                self.warn('conditionally-assigned', node, diff)

        common = set(if_scope.names()) | set(else_scope.names())
        for name in common:
            types = [if_scope.get_type(name), else_scope.get_type(name)]
            unified_type = unify_types(types)
            self._context.add_symbol(name, unified_type)
            if isinstance(unified_type, Unknown):
                if not any(isinstance(x, Unknown) for x in types):
                    self.warn('conditional-type', node, name)

        return_types = [if_scope.get_return_type() or Unknown(),
                        else_scope.get_return_type() or Unknown()]
        unified_return_type = unify_types(return_types)
        self._context.set_return(unified_return_type)
        if isinstance(unified_return_type, Unknown):
            if not any(isinstance(x, Unknown) for x in return_types):
                self.warn('conditional-return-type', node)

    def visit_While(self, node):
        self.check_type(node.test, Bool)
        self.generic_visit(node)

    def visit_Slice(self, node):
        if node.lower is not None:
            self.check_type(node.lower, Num)
        if node.upper is not None:
            self.check_type(node.upper, Num)
        if node.step is not None:
            self.check_type(node.step, Num)
        self.generic_visit(node)

    def visit_Index(self, node):
        # index can mean list index or dict lookup, so could be any type
        self.generic_visit(node)

    def visit_BinOp(self, node):
        operator = get_token(node.op)
        types = [self.expr_type(node.left), self.expr_type(node.right)]
        known = known_types(types)
        if operator == 'Mult':
            self.check_type_set(node, types, ({Num}, {Num, Str}))
        elif operator == 'Add':
            if len(known) > 1:
                if not all(isinstance(x, Tuple) for x in known):
                    details = ', '.join([str(x) for x in types])
                    self.warn('inconsistent-types', node, details)
            elif len(known) == 1:
                self.check_type(node, (Num, Str, List, Tuple),
                    override=iter(known).next())
        elif operator == 'Mod':
            if not isinstance(types[0], (Str, Unknown)):
                self.check_type(node.left, Num)
                self.check_type(node.right, Num)
        else:
            self.check_type(node.left, Num)
            self.check_type(node.right, Num)
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        operator = get_token(node.op)
        if operator == 'Not':
            self.check_type(node.operand, Bool)
        else:
            self.check_type(node.operand, Num)
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.check_type(node.test, Bool)
        self.consistent_types(unifiable_types, node, [node.body, node.orelse])
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
        self.consistent_types(unifiable_types, node, node.elts)

    def visit_Dict(self, node):
        self.consistent_types(unifiable_types, node, node.keys)
        self.consistent_types(unifiable_types, node, node.values)

    def visit_Set(self, node):
        self.consistent_types(unifiable_types, node, node.elts)

    def visit_ListComp(self, node):
        self.begin_scope()
        assign_generators(node.generators, self._context)
        self.generic_visit(node)
        self.end_scope()

    def visit_DictComp(self, node):
        self.begin_scope()
        assign_generators(node.generators, self._context)
        self.generic_visit(node)
        self.end_scope()

    def visit_SetComp(self, node):
        self.begin_scope()
        assign_generators(node.generators, self._context)
        self.generic_visit(node)
        self.end_scope()

    def visit_GeneratorExp(self, node):
        self.begin_scope()
        assign_generators(node.generators, self._context)
        self.generic_visit(node)
        self.end_scope()


def analyze(source, filepath=None, context=None, imported=[]):
    tree = ast.parse(source, filepath)
    visitor = Visitor(filepath, context, imported)
    visitor.visit(tree)
    return visitor.report()


def analysis(source, filepath=None):
    scope, warnings, _ = analyze(source, filepath)
    warning_output = ''.join([str(warning) + '\n' for warning in warnings])
    scope_output = str(scope)
    separator = '\n' if warning_output and scope_output else ''
    return scope_output + separator + warning_output


def main():
    filepath = sys.argv[1]
    with open(filepath) as source_file:
        source = source_file.read()
    sys.stdout.write(analysis(source, filepath))


if __name__ == '__main__':
    main()
