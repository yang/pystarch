import expr
from type_objects import List, Dict, Unknown


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
            self.explicit_types = []
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
        self.explicit_types = self.get_explicit_argtypes(
            decorator_list, context)
        self.types = [explicit if explicit != Unknown() else default
            for explicit, default
            in zip(self.explicit_types, self.default_types)]
        self.vararg_name = arguments.vararg
        self.kwarg_name = arguments.kwarg

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
        arguments.explicit_types = other_arguments.explicit_types[1:]
        arguments.min_count = max(0, other_arguments.min_count - 1)
        arguments.vararg_name = other_arguments.vararg_name
        arguments.kwarg_name = other_arguments.kwarg_name
        return arguments

    def get_dict(self):
        return dict(zip(self.names, self.types))

    def get_explicit_argtypes(self, decorator_list, context):
        types_decorator = [d for d in decorator_list
            if get_token(d) == 'Call' and d.func.id == 'types']
        if len(types_decorator) == 1:
            argtypes, kwargtypes = call_argtypes(types_decorator[0], context)
        else:
            argtypes, kwargtypes = [], {}
        return argtypes + [kwargtypes.get(name, Unknown())
            for name in self.names[len(argtypes):]]

    def load_context(self, context):
        for name, argtype in self.get_dict().items():
            context.add_symbol(name, argtype)
        if self.vararg_name:
            context.add_symbol(self.vararg_name, List(Unknown()))
        if self.kwarg_name:
            context.add_symbol(self.kwarg_name, Dict(Unknown(), Unknown()))

    def __str__(self):
        vararg = (', {0}: Tuple'.format(self.vararg_name)
            if self.vararg_name else '')
        kwarg = (', {0}: Dict'.format(self.kwarg_name)
            if self.kwarg_name else '')
        return (', '.join(name + ': ' + str(argtype) for name, argtype
            in zip(self.names, self.types)) + vararg + kwarg)


def load_argument_symbols(arguments, scope):
    for argument in arguments.args:
        scope.add(argument.id, Unknown())
    if node.vararg is not None:
        scope.add(node.vararg.id, List(Unknown()))
    if node.kwarg is not None:
        scope.add(node.kwarg.id, Dict(Unknown(), Unknown()))


def construct_function_type(node, visitor):  # FunctionDef node
    visitor.begin_scope()
    load_argument_symbols(node.args, visitor.scope())
    visitor.visit(node.body)
    scope = visitor.end_scope()
