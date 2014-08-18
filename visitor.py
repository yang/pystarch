# pylint: disable=invalid-name
import sys
import os
import ast
from warning import NodeWarning
from backend import expression_type, call_argtypes, Arguments, \
    assign, make_argument_scope, get_token, assign_generators, \
    unify_types, known_types, Context, ExtendedContext, Scope, Union, \
    static_evaluate, UnknownValue, NoneType, Bool, Num, Str, List, Dict, \
    Tuple, Instance, Class, Function, Maybe, Unknown, comparable_types, \
    type_patterns, maybe_inferences, unifiable_types, Symbol, type_subset, \
    BaseTuple, find_constraints, construct_function_type, type_intersection


class ScopeVisitor(ast.NodeVisitor):
    def __init__(self, filepath='', context=None, imported=[]):
        ast.NodeVisitor.__init__(self)
        self._filepath = filepath
        self._warnings = []
        self._context = context if context is not None else builtin_context()
        self._imported = imported
        self._annotations = []
        self._class_name = None     # the name of the class we are inside

    def scope(self):
        return self._context.get_top_scope()

    def context(self):
        return ExtendedContext(self._context)

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
        return expression_type(node, self.context())

    def evaluate(self, node):
        return static_evaluate(node, self.context())

    def consistent_types(self, check_func, root_node, nodes):
        types = [self.expr_type(node) for node in nodes]
        if not check_func(types):
            details = ', '.join([str(x) for x in types])
            self.warn('inconsistent-types', root_node, details)

    def apply_constraints(self, node, required_type=Unknown()):
        constraints = find_constraints(node, required_type, self.context())
        for name, constrained_type in constraints:
            symbol = self._context.get(name)
            if symbol is not None:
                new_type = symbol.add_constraint(constrained_type)
                if new_type is None:
                    self.warn('type-error', node, name)

    def check_type(self, node, type_):
        self.apply_constraints(node, type_)
        expr_type = self.expr_type(node)
        if not type_subset(expr_type, type_):
            details = '{0} vs {1}'.format(expr_type, type_)
            self.warn('type-error', node, details)

    def check_type_pattern(self, node, types, patterns):
        if not any(all(type_subset(x, y) for x, y in zip(types, pattern))
               for pattern in patterns):
            got = ', '.join([str(x) for x in types])
            fmt = lambda s: '(' + ', '.join(str(x) for x in sorted(s)) + ')'
            options = ' or '.join([fmt(x) for x in patterns])
            details = '[{0}] vs {1}'.format(got, options)
            self.warn('type-error', node, details)

    def check_return(self, node, is_yield=False):
        value_type = self.expr_type(node.value)
        return_type = List(value_type) if is_yield else value_type
        static_value = self.evaluate(node.value)
        previous_type = self._context.get_type()
        if previous_type is None:
            self._context.set_return(Symbol(
                'return', return_type, static_value))
            return
        new_type = unify_types([previous_type, return_type])
        if new_type == Unknown():
            details = '{0} -> {1}'.format(previous_type, return_type)
            self.warn('multiple-return-types', node, details)
        else:
            self._context.set_return(Symbol('return', new_type, static_value))

    def check_assign(self, node, target, value, generator=False):
        assignments = assign(target, value, self._context, generator=generator)
        for name, old_symbol, new_symbol in assignments:
            if old_symbol is not None:
                self.warn('reassignment', node, name)
                if new_symbol.get_type() != old_symbol.get_type():
                    details = '{0}: {1} -> {2}'.format(
                        name, old_symbol.get_type(), new_symbol.get_type())
                    self.warn('type-change', node, details)

    def visit_Name(self, node):
        the_type = self._context.get_type(node.id)
        if the_type is None:
            self.warn('undefined', node)
        if not isinstance(the_type, Unknown):
            label = str(the_type) if the_type else None
            annotation = (self._filepath, node.lineno, node.col_offset,
                          node.id, label)
            self._annotations.append(annotation)

    def visit_ClassDef(self, node):
        self._class_name = node.name
        self.begin_scope()
        self.generic_visit(node)
        scope = self.end_scope()
        self._class_name = None
        # TODO: handle case of no __init__ function
        if '__init__' in scope:
            init_arguments = scope.get_type('__init__').arguments
            arguments = Arguments.copy_without_first_argument(init_arguments)
            instance_type = scope.get_type('__init__').return_type
            common = set(scope.names()) & set(instance_type.attributes.names())
            if len(common) > 0:
                self.warn(node, 'overlapping-class-names', ','.join(common))
            instance_type.attributes.merge(scope)
        else:
            arguments = Arguments()
            instance_type = Instance(node.name, Scope())
        # TODO: separate class/static methods and attributes from the rest
        class_type = Class(node.name, arguments, instance_type, Scope())
        # TODO: save self.x into scope where "self" is 1st param to init
        self._context.add(Symbol(node.name, class_type, UnknownValue()))

    def visit_FunctionDef(self, node):
        visitor = ScopeVisitor(self._filepath, self.context())
        function_type, warnings, annotations = construct_function_type(
            node, visitor)
        self._context.add(Symbol(node.name, function_type, UnknownValue()))

        self._annotations.extend(annotations)
        self._warnings.extend(warnings)

        # now check that all the types are consistent between
        # the default types, annotated types, and constrained types
        arguments = function_type.arguments
        types = zip(arguments.names, arguments.types,
            arguments.annotated_types, arguments.default_types)
        for name, constrained_type, annotated_type, default_type in types:
            if (annotated_type != Unknown() and default_type != Unknown() and
                    default_type != annotated_type):
                self.warn('default-argument-type-error', node, name)

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
        func_type = expression_type(node.func, self._context)
        if isinstance(func_type, Unknown):
            return self.warn('undefined-function', node)
        if not isinstance(func_type, (Function, Class)):
            return self.warn('not-a-function', node)

        argtypes, kwargtypes = call_argtypes(node, self.context())
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
        self.apply_constraints(node.value)
        self.check_return(node)
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.check_return(node, is_yield=True)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self.check_assign(node, target, node.value)
        types = map(self.expr_type, node.targets + [node.value])
        intersection = reduce(type_intersection, types)
        self.apply_constraints(node.value, intersection)
        for target in node.targets:
            self.apply_constraints(target, intersection)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign(node, node.target, node.value)
        types = map(self.expr_type, [node.target, node.value])
        intersection = type_intersection(*types)
        self.apply_constraints(node.target, intersection)
        self.apply_constraints(node.value, intersection)
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
            self.check_type(value, Bool())
        self.generic_visit(node)

    def visit_Delete(self, node):
        # TODO: need to support identifiers, dict items, attributes, list items
        #names = [target.id for target in node.targets]
        self.warn('delete', node)
        self.generic_visit(node)

    def _visit_branch(self, body, inferences):
        # Note: need two scope layers, first for inferences and
        # second for symbols that are assigned within the branch
        if body is None:
            return Scope()
        self.begin_scope()  # inferences scope
        for name, type_ in inferences.iteritems():
            self._context.add(Symbol(name, type_, UnknownValue()))
        self.begin_scope()
        for stmt in body:
            self.visit(stmt)
        scope = self.end_scope()
        self.end_scope()        # inferences scope
        return scope

    def visit_If(self, node):
        self.visit(node.test)   # is this necessary?
        self.check_type(node.test, Bool())
        test_value = static_evaluate(node.test, self.context())
        if not isinstance(test_value, UnknownValue):
            self.warn('constant-if-condition', node)

        ext_ctx = self.context()
        if_inferences, else_inferences = maybe_inferences(node.test, ext_ctx)
        if_scope = self._visit_branch(node.body, if_inferences)
        else_scope = self._visit_branch(node.orelse, else_inferences)

        diffs = set(if_scope.names()) ^ set(else_scope.names())
        for diff in diffs:
            if diff not in self._context:
                self.warn('conditionally-assigned', node, diff)

        common = set(if_scope.names()) & set(else_scope.names())
        for name in common:
            types = [if_scope.get_type(name), else_scope.get_type(name)]
            unified_type = unify_types(types)
            self._context.add(Symbol(name, unified_type, UnknownValue()))
            if isinstance(unified_type, Unknown):
                if not any(isinstance(x, Unknown) for x in types):
                    self.warn('conditional-type', node, name)

        return_types = [if_scope.get_type() or Unknown(),
                        else_scope.get_type() or Unknown()]
        unified_return_type = unify_types(return_types)
        self._context.set_return(Symbol('return', unified_return_type,
            UnknownValue()))
        if isinstance(unified_return_type, Unknown):
            if not any(isinstance(x, Unknown) for x in return_types):
                self.warn('conditional-return-type', node)

    def visit_While(self, node):
        self.check_type(node.test, Bool())
        self.generic_visit(node)

    def visit_Slice(self, node):
        if node.lower is not None:
            self.check_type(node.lower, Num())
        if node.upper is not None:
            self.check_type(node.upper, Num())
        if node.step is not None:
            self.check_type(node.step, Num())
        self.generic_visit(node)

    def visit_Index(self, node):
        # index can mean list index or dict lookup, so could be any type
        self.check_type(node.value, Union(List(Unknown()), BaseTuple(),
                                          Dict(Unknown(), Unknown())))
        self.generic_visit(node)

    def visit_BinOp(self, node):
        operator = get_token(node.op)
        types = [self.expr_type(node.left), self.expr_type(node.right)]
        known = known_types(types)
        if operator == 'Mult':
            self.check_type_pattern(node, types,
                ([Num(), Num()], [Num(), Str()], [Str(), Num()]))
        elif operator == 'Add':
            if len(known) > 1:
                if not all(isinstance(x, Tuple) for x in known):
                    details = ', '.join([str(x) for x in types])
                    self.warn('inconsistent-types', node, details)
            elif len(known) == 1:
                union_type = Union(Num(), Str(), List(Unknown()), BaseTuple())
                self.check_type(node.left, union_type)
                self.check_type(node.right, union_type)
        elif operator == 'Mod':
            if not isinstance(types[0], (Str, Unknown)):
                self.check_type(node.left, Num())
                self.check_type(node.right, Num())
        else:
            self.check_type(node.left, Num())
            self.check_type(node.right, Num())
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        operator = get_token(node.op)
        if operator == 'Not':
            self.check_type(node.operand, Bool())
        else:
            self.check_type(node.operand, Num())
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.check_type(node.test, Bool())
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

    def visit_Expr(self, node):
        self.check_type(node.value, Unknown())    # trigger find_constraints

