# pylint: disable=invalid-name
import ast
from warning import Warnings
from backend import visit_expression, assign, unify_types, ExtendedContext, \
    Scope, static_evaluate, UnknownValue, NoneType, Bool, List, Instance, \
    Class, Unknown, maybe_inferences, Symbol, type_subset, Context, \
    construct_function_type, FunctionSignature, ClassEvaluator, Union, Set, \
    Dict, Str


class ScopeVisitor(ast.NodeVisitor):
    def __init__(self, filepath='', context=None, imported=[], warnings=None):
        ast.NodeVisitor.__init__(self)
        self._filepath = filepath
        self._warnings = Warnings(filepath) if warnings is None else warnings
        self._context = context if context is not None else Context()
        self._imported = imported
        self._annotations = []
        self._class_instance = None

    def clone(self):
        return ScopeVisitor(self._filepath, self.context(), self._imported)

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

    def begin_scope(self, scope=None):
        self._context.begin_scope(scope)

    def end_scope(self):
        return self._context.end_scope()

    def merge_scope(self, scope):
        self._context.merge_scope(scope)

    def warn(self, category, node, details=None):
        self._warnings.warn(node, category, details)

    def evaluate(self, node):
        return static_evaluate(node, self.context())

    def check_type(self, node, expected_type=Unknown()):
        computed_type = visit_expression(node, expected_type, self.context(),
                                         self._warnings)
        if not type_subset(computed_type, expected_type):
            details = '{0} vs {1}'.format(computed_type, expected_type)
            self.warn('type-error', node, details)
        return computed_type

    def check_assign(self, node, target, value, generator=False):
        assignments = assign(target, value, self._context,
                             self._warnings, generator=generator)
        for name, old_symbol, new_symbol in assignments:
            if old_symbol is not None:
                self.warn('reassignment', node, name)
                if new_symbol.get_type() != old_symbol.get_type():
                    details = '{0}: {1} -> {2}'.format(
                        name, old_symbol.get_type(), new_symbol.get_type())
                    self.warn('type-change', node, details)

    def visit_ClassDef(self, node):
        # ignore warnings on the first pass because we don't have an
        # instance to pass in as "self"
        visitor = ScopeVisitor(self._filepath, self.context())
        visitor.begin_scope()
        visitor.generic_visit(node)
        scope = visitor.end_scope()
        if '__init__' in scope:
            signature = scope.get_type('__init__').signature
        else:
            signature = FunctionSignature('__init__')   # TODO: add self arg?
        return_type = Instance(node.name, Scope())      # dummy instance
        # TODO: separate class/static methods and attributes from the rest
        class_type = Class(node.name, signature, return_type, None, scope)
        class_type.evaluator = ClassEvaluator(class_type)
        self._context.add(Symbol(node.name, class_type))

        # now visit the class contents to generate warnings
        argument_scope = signature.generic_scope()
        self._class_instance = class_type.evaluator.evaluate(argument_scope)[0]
        self.begin_scope()
        self.generic_visit(node)        # now all functiondefs have access
        self.end_scope()                # to class instance to load "self"
        self._class_instance = None

    def visit_FunctionDef(self, node):
        visitor = ScopeVisitor(self._filepath, self.context(),
                               warnings=self._warnings)
        function_type = construct_function_type(node, visitor,
                                                self._class_instance)
        self._context.add(Symbol(node.name, function_type))

        # now check that all the types are consistent between
        # the default types, annotated types, and constrained types
        signature = function_type.signature
        types = zip(signature.names, signature.types,
                    signature.annotated_types, signature.default_types)
        for name, _, annotated_type, default_type in types:
            if (annotated_type != Unknown() and default_type != Unknown() and
                    default_type != annotated_type):
                self.warn('default-argument-type-error', node, name)

    def _check_return(self, return_type, static_value=None):
        previous_type = self._context.get_type()
        new_type = (unify_types([previous_type, return_type])
                    if previous_type is not None else return_type)
        value = (static_value or UnknownValue() if previous_type is None else
                 UnknownValue())
        self._context.set_return(Symbol('return', new_type, value))

    def check_return(self, node, is_yield=False):
        if node.value is None:
            value_type = NoneType()
        else:
            value_type = self.check_type(node.value, Unknown())
        return_type = List(value_type) if is_yield else value_type
        static_value = self.evaluate(node.value)
        self._check_return(return_type, static_value)

    def visit_Return(self, node):
        self.check_return(node)
        self.generic_visit(node)

    def visit_Yield(self, node):    # not sure why python makes yield an expr
        self.check_return(node, is_yield=True)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self.check_assign(node, target, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.check_assign(node, node.target, node.value)
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
        self.begin_scope(Scope(inferences))
        self.begin_scope()
        for stmt in body:
            self.visit(stmt)
        scope = self.end_scope()
        self.end_scope()
        return_type = scope.get_type()
        if return_type is not None:
            self._check_return(return_type, scope.get_value())
        return scope

    def visit_If(self, node):
        self.check_type(node.test, Bool())
        test_value = static_evaluate(node.test, self.context())
        if not isinstance(test_value, UnknownValue):
            self.warn('constant-if-condition', node)

        ext_ctx = self.context()
        if_inferences, else_inferences = maybe_inferences(node.test, ext_ctx)

        # don't visit unreachable code
        if test_value is True:
            self._visit_branch(node.body, if_inferences)
            return
        if test_value is False:
            self._visit_branch(node.orelse, else_inferences)
            return

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
            self._context.add(Symbol(name, unified_type))
            if isinstance(unified_type, Unknown):
                if not any(isinstance(x, Unknown) for x in types):
                    self.warn('conditional-type', node, name)

    def visit_While(self, node):
        self.check_type(node.test, Bool())
        self.generic_visit(node)

    def visit_For(self, node):
        # Python doesn't create a scope for "for", but we will
        # treat it as if it did because it should
        union_type = Union(List(Unknown()), Set(Unknown()),
                           Dict(Unknown(), Unknown()), Str())
        self.check_type(node.iter, union_type)
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

    def visit_Expr(self, node):
        self.check_type(node.value, Unknown())

    def visit_Import(self, node):
        self.warn('non-global-import', node)

    def visit_ImportFrom(self, node):
        self.warn('non-global-import', node)
