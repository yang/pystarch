import expr
from context import Symbol, Scope
from type_objects import List, Dict, Unknown, Function, NoneType, Instance
from util import type_intersection


def get_token(node):
    return node.__class__.__name__


def call_argtypes(call_node, context):
    types = []
    keyword_types = {}
    for arg in call_node.args:
        types.append(expr.expression_type(arg, context))
    for keyword in call_node.keywords:
        keyword_types[keyword.arg] = expr.expression_type(
                                          keyword.value, context)
    if call_node.starargs is not None:
        keyword_types['*args'] = expr.expression_type(call_node.starargs,
                                                      context)
    if call_node.kwargs is not None:
        keyword_types['**kwargs'] = expr.expression_type(call_node.kwargs,
                                                         context)
    return types, keyword_types


# "arguments" parameter is node.args for FunctionDef or Lambda
class Arguments(object):
    def __init__(self, arguments=None, context=None, decorator_list=[]):
        if arguments is None:
            self.names = []
            self.types = []
            self.default_types = []
            self.annotated_types = []
            self.vararg_name = None
            self.kwarg_name = None
            self.min_count = 0
            return      # only for copy constructor below
        assert context is not None
        self.names = [arg.id for arg in arguments.args]
        self.min_count = len(arguments.args) - len(arguments.defaults)
        default_types = [expr.expression_type(d, context)
                            for d in arguments.defaults]
        self.default_types = ([Unknown()] * self.min_count) + default_types
        self.annotated_types = self._get_annotated_types(
            decorator_list, context)
        self.types = [annotated if annotated != Unknown() else default
            for annotated, default
            in zip(self.annotated_types, self.default_types)]
        self.vararg_name = arguments.vararg
        self.kwarg_name = arguments.kwarg

    def __hash__(self):
        return hash(tuple(self.types))

    def __contains__(self, name):
        return name in self.names

    def __len__(self):
        return len(self.names)

    def __getitem__(self, index):
        return zip(self.names, self.types)[index]

    @classmethod
    def copy_without_first_argument(cls, other_arguments):
        arguments = cls()
        arguments.names = other_arguments.names[1:]
        arguments.types = other_arguments.types[1:]
        arguments.default_types = other_arguments.default_types[1:]
        arguments.annotated_types = other_arguments.annotated_types[1:]
        arguments.min_count = max(0, other_arguments.min_count - 1)
        arguments.vararg_name = other_arguments.vararg_name
        arguments.kwarg_name = other_arguments.kwarg_name
        return arguments

    def constrain_type(self, name, type_):
        for i, arg_name in enumerate(self.names):
            if arg_name == name:
                intersection = type_intersection(type_, self.types[i])
                if intersection is not None:
                    self.types[i] = intersection
                    return intersection
                else:
                    return None

    def constrain_types(self, constraints):
        for name in self.names:
            if name in constraints:
                self.constrain_type(name, constraints[name])

    def get_signature(self):
        return zip(self.names, self.types)

    def get_dict(self):
        return dict(self.get_signature())

    def _get_annotated_types(self, decorator_list, context):
        types_decorator = [d for d in decorator_list
            if get_token(d) == 'Call' and d.func.id == 'types']
        if len(types_decorator) == 1:
            argtypes, kwargtypes = call_argtypes(types_decorator[0], context)
        else:
            argtypes, kwargtypes = [], {}
        return argtypes + [kwargtypes.get(name, Unknown())
            for name in self.names[len(argtypes):]]

    def load_scope(self, scope, call_node=None):
        # TODO: process call_node arguments
        for name, argtype in self.get_dict().items():
            scope.add(Symbol(name, argtype))
        if self.vararg_name:
            scope.add(Symbol(self.vararg_name, List(Unknown())))
        if self.kwarg_name:
            scope.add(Symbol(self.kwarg_name, Dict(Unknown(), Unknown())))

    def __str__(self):
        vararg = (', {0}: Tuple'.format(self.vararg_name)
            if self.vararg_name else '')
        kwarg = (', {0}: Dict'.format(self.kwarg_name)
            if self.kwarg_name else '')
        return (', '.join(name + ': ' + str(argtype) for name, argtype
            in zip(self.names, self.types)) + vararg + kwarg)


# we only generate warnings on the first pass through a function definition
# the FunctionEvaluator is only to evaluate the type and static value of
# function calls
class FunctionEvaluator(object):
    def __init__(self, functiondef_node, visitor):
        self._name = getattr(functiondef_node, 'name', None)
        self._arguments = Arguments(functiondef_node.args, visitor.context())
        self._body = functiondef_node.body
        self._visitor = visitor
        visitor.context().clear_constraints()
        return_type, static_value = self.evaluate()
        self._arguments.constrain_types(visitor.context().get_constraints())
        self._return_type = return_type
        self._static_value = static_value

    def get_signature(self):
        return self._arguments.get_signature(), self._return_type

    def _evaluate(self, call_node=None):
        visitor = self._visitor
        visitor.begin_scope()
        self._arguments.load_scope(visitor.scope(), call_node)
        for stmt in self._body:
            visitor.visit(stmt)
        return visitor.end_scope()

    def evaluate(self, call_node=None):
        scope = self._evaluate(call_node)
        if self._name == '__init__':
            return_type = Instance('Class', Scope()) # TODO
        else:
            return_type = scope.get_type() or NoneType()
        if return_type != NoneType():
            return_value = scope.get_value() or UnknownValue()
        else:
            return_value = None
        return return_type, return_value


def construct_function_type(functiondef_node, visitor):
    return Function(FunctionEvaluator(functiondef_node, visitor))
