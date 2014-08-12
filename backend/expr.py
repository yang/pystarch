"""This file should not make any changes to the context or try to do any
type validation. If there is a problem with the types, it should do some
default behavior or raise an exception if there is no default behavior."""
from functools import partial
from context import Scope, Symbol
from type_objects import Bool, Num, Str, List, Tuple, Set, \
    Dict, Function, Instance, Unknown, NoneType, Class
from evaluate import static_evaluate, UnknownValue
from util import unique_type, unify_types
from assign import assign


def get_token(node):
    return node.__class__.__name__


def call_argtypes(call_node, context):
    types = []
    keyword_types = {}
    for arg in call_node.args:
        types.append(expression_type(arg, context))
    for keyword in call_node.keywords:
        keyword_types[keyword.arg] = expression_type(keyword.value, context)
    if call_node.starargs is not None:
        keyword_types['*args'] = expression_type(call_node.starargs, context)
    if call_node.kwargs is not None:
        keyword_types['**kwargs'] = expression_type(call_node.kwargs, context)
    return types, keyword_types


def add_scope_symbol(scope, name, node, context):
    typ = expression_type(node, context)
    value = static_evaluate(node, context)
    scope.add(Symbol(name, typ, value))


# context is the context at call-time, not definition-time
def make_argument_scope(call_node, arguments, context):
    scope = Scope()
    for name, value in zip(arguments.names, call_node.args):
        add_scope_symbol(scope, name, value, context)
    for keyword in call_node.keywords:
        if keyword.arg in arguments.names:
            add_scope_symbol(scope, keyword.arg, keyword.value, context)
    if call_node.starargs is not None and arguments.vararg_name is not None:
        add_scope_symbol(scope, arguments.vararg_name, call_node.starargs,
            context)
    if call_node.kwargs is not None and arguments.kwarg_name is not None:
        add_scope_symbol(scope, arguments.kwarg_name, call_node.kwargs,
            context)
    return scope


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
        default_types = [expression_type(d, context)
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


def assign_generators(generators, context):
    for generator in generators:
        assign(generator.target, generator.iter, context, generator=True)


def comprehension_type(element, generators, context):
    context.begin_scope()
    assign_generators(generators, context)
    element_type = expression_type(element, context)
    context.end_scope()
    return element_type


# Note: "True" and "False" evalute to Bool because they are symbol
# names that have their types builtin to the default context. Similarly,
# "None" has type NoneType.
# If type cannot be positively determined, then this will return Unknown.
# Note that this does not mean that errors will always return Unknown, for
# example, 2 / 'a' will still return Num because the division operator
# must always return Num. Similarly, "[1,2,3] + Unknown" will return List(Num)
def expression_type(node, context):
    """
    This function determines the type of an expression, but does
    not do any type validation.
    """
    recur = partial(expression_type, context=context)
    token = get_token(node)
    if token == 'BoolOp':
        return Bool()   # more restrictive than Python
    if token == 'BinOp':
        types = [recur(node.left), recur(node.right)]
        operator = get_token(node.op)
        if operator == 'Mult':
            types_set = set(types)
            if types_set == {Num()}:
                return Num()
            elif types_set == {Num(), Str()}:
                return Str()
            elif types_set == {Str(), Unknown()}:
                return Str()
            else:
                return Unknown()
        elif operator == 'Add':
            if all(isinstance(x, Tuple) for x in types):
                item_types = types[0].item_types + types[1].item_types
                return Tuple(item_types)
            else:
                operand_type = unique_type(types)
                if isinstance(operand_type, (Num, Str, List)):
                    return operand_type
                else:
                    return Unknown()
        elif operator == 'Mod':
            if isinstance(recur(node.left), Str):
                return Str()
            else:
                return Num()
        else:
            return Num()
    if token == 'UnaryOp':
        return Bool() if get_token(node.op) == 'Not' else Num()
    if token == 'Lambda':
        return Function(Arguments(node.args, context), recur(node.body))
    if token == 'IfExp':
        return unify_types([recur(node.body), recur(node.orelse)])
    if token == 'Dict':
        key_type = unify_types([recur(key) for key in node.keys])
        value_type = unify_types([recur(value) for value in node.values])
        return Dict(key_type, value_type)
    if token == 'Set':
        return Set(unify_types([recur(elt) for elt in node.elts]))
    if token == 'ListComp':
        return List(comprehension_type(node.elt, node.generators, context))
    if token == 'SetComp':
        return Set(comprehension_type(node.elt, node.generators, context))
    if token == 'DictComp':
        key_type = comprehension_type(node.key, node.generators, context)
        value_type = comprehension_type(node.value, node.generators, context)
        return Dict(key_type, value_type)
    if token == 'GeneratorExp':
        return List(comprehension_type(node.elt, node.generators, context))
    if token == 'Yield':
        return List(recur(node.value))
    if token == 'Compare':
        return Bool()
    if token == 'Call':
        function_type = recur(node.func)
        if isinstance(function_type, Class):
            return function_type.return_type
        if not isinstance(function_type, Function):
            return Unknown()
        arguments = function_type.arguments
        argument_scope = make_argument_scope(node, arguments, context)
        return_type, _, _ = function_type.return_type(argument_scope)
        return return_type
    if token == 'Repr':    # TODO: is Repr a Str?
        return Str()
    if token == 'Num':
        return Num()
    if token == 'Str':
        return Str()
    if token == 'Attribute':
        value_type = recur(node.value)
        if not isinstance(value_type, Instance):
            return Unknown()
        return value_type.attributes.get_type(node.attr) or Unknown()
    if token == 'Subscript':
        value_type = recur(node.value)
        if get_token(node.slice) == 'Index':
            if isinstance(value_type, Tuple):
                index = static_evaluate(node.slice.value, context)
                if isinstance(index, UnknownValue):
                    return Unknown()
                if not isinstance(index, int):
                    return Unknown()
                if not 0 <= index < len(value_type.item_types):
                    return Unknown()
                return value_type.item_types[index]
            elif isinstance(value_type, List):
                return value_type.item_type
            elif isinstance(value_type, Dict):
                return value_type.value_type
            else:
                return Unknown()
        else:
            return value_type
    if token == 'Name':
        return context.get_type(node.id) or Unknown()
    if token == 'List':
        return List(unify_types([recur(elt) for elt in node.elts]))
    if token == 'Tuple':
        return Tuple([recur(element) for element in node.elts])
    if token == 'NoneType':
        return NoneType()
    if token == 'Unknown':
        return Unknown()
    raise Exception('expression_type does not recognize ' + token)
