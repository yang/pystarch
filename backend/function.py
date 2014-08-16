import expr
from context import Symbol, Scope
from type_objects import List, Dict, Unknown, Function, NoneType, Instance
from constraints import find_constraints
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

    def get_dict(self):
        return dict(zip(self.names, self.types))

    def _get_annotated_types(self, decorator_list, context):
        types_decorator = [d for d in decorator_list
            if get_token(d) == 'Call' and d.func.id == 'types']
        if len(types_decorator) == 1:
            argtypes, kwargtypes = call_argtypes(types_decorator[0], context)
        else:
            argtypes, kwargtypes = [], {}
        return argtypes + [kwargtypes.get(name, Unknown())
            for name in self.names[len(argtypes):]]

    def load_scope(self, scope):
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


def analyze_function(node, arguments, visitor):
    visitor.begin_scope()
    arguments.load_scope(visitor.scope())
    for stmt in node.body:
        visitor.visit(stmt)
    scope = visitor.end_scope()
    _, warnings, annotations = visitor.report()
    return_type = scope.get_type() or NoneType()
    return return_type, warnings, annotations


def construct_function_type(node, visitor):  # FunctionDef node
    visitor.begin_scope()
    arguments = Arguments(node.args, visitor.context())
    arguments.load_scope(visitor.scope())
    for stmt in node.body:
        visitor.visit(stmt)
    scope = visitor.end_scope()
    for argument in node.args.args:
        if argument.id in scope:
            arguments.constrain_type(argument.id, scope.get_type(argument.id))
    return_type, warnings, annotations = analyze_function(
        node, arguments, visitor)
    if node.name == '__init__':
        return_type = Instance('Class', Scope()) # TODO
    return Function(arguments, return_type), warnings, annotations
