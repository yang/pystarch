from functools import partial
from context import Scope, Symbol
from type_objects import Bool, Num, Str, List, Tuple, Set, BaseTuple, \
    Dict, Function, Instance, Unknown, NoneType, Class, Union, Maybe
from evaluate import static_evaluate, UnknownValue
from util import unique_type, unify_types, type_intersection, type_subset
from assign import assign
from function import Arguments, call_argtypes


def get_token(node):
    return node.__class__.__name__


def add_scope_symbol(scope, name, node, context):
    typ = expression_type(node, context)
    value = static_evaluate(node, context)
    scope.add(Symbol(name, typ, value))


def type_error(node, label, got, expected, warnings):
    template = '{0} expected type {1} but got {2}'
    expected_str = [str(x) for x in expected]
    details = template.format(label, ' or '.join(expected_str), str(got))
    warnings.warn(node, 'type-error', details)


def check_argument_type(node, label, got, expected, warnings):
    assert isinstance(expected, list)
    if Unknown() not in expected and got not in expected + [NoneType()]:
        type_error(node, 'Argument ' + str(label), got, expected, warnings)


def check_consistent_types(node, types, expected_type, context, warnings):
    unified = unify_types(types + [expected_type])
    result = unified if not isinstance(unified, Unknown) else unify_types(types)
    if isinstance(unified, Unknown):
        details = ', '.join([str(x) for x in types])
        warnings.warn(node, 'inconsistent-types', details)


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


def assign_generators(generators, context, warnings):
    for generator in generators:
        assign(generator.target, generator.iter, context,
               warnings, generator=True)


def comprehension_type(element, generators, expected_element_type,
                       context, warnings):
    context.begin_scope()
    assign_generators(generators, context, warnings)
    element_type = visit_expression(element, expected_element_type,
                                   context, warnings)
    context.end_scope()
    return element_type


class NullWarnings:
    def warn(self, node, category, details=None):
        pass


# Note: "True" and "False" evalute to Bool because they are symbol
# names that have their types builtin to the default context. Similarly,
# "None" has type NoneType.
# If type cannot be positively determined, then this will return Unknown.
# Note that this does not mean that errors will always return Unknown, for
# example, 2 / 'a' will still return Num because the division operator
# must always return Num. Similarly, "[1,2,3] + Unknown" will return List(Num)

def visit_expression(node, expected_type, context, warnings=NullWarnings()):
    result_type = _visit_expression(node, expected_type, context, warnings)
    if (not type_subset(result_type, expected_type)
        and not isinstance(result_type, Unknown)):
        details = '{0} vs {1}'.format(result_type, expected_type)
        warnings.warn(node, 'type-error', details)
    return result_type


def _visit_expression(node, expected_type, context, warnings):
    recur = partial(visit_expression, context=context, warnings=warnings)
    probe = partial(expression_type, context=context)
    comp = partial(comprehension_type, context=context, warnings=warnings)

    token = get_token(node)
    if token == 'BoolOp':
        for expr in node.values:
            recur(expr, Bool())
        return Bool()   # more restrictive than Python
    if token == 'BinOp':
        operator = get_token(node.op)
        if operator == 'Add':
            union_type = Union(Num(), Str(), List(Unknown))
            intersect = type_intersection(probe(node.left), probe(node.right))
            result_type = type_intersection(intersect, union_type)
            recur(node.left, result_type or union_type)
            recur(node.right, result_type or union_type)
            return result_type if result_type else Unknown()
        elif operator == 'Mult':
            union_type = Union(Num(), Str())
            left_probe = probe(node.left)
            right_probe = probe(node.right)
            if isinstance(left_probe, Str):
                recur(node.left, Str())
                recur(node.right, Num())
                return Str()
            if isinstance(right_probe, Str):
                recur(node.left, Num())
                recur(node.right, Str())
                return Str()
            if isinstance(left_probe, Num) and isinstance(right_probe, Num):
                recur(node.left, Num())
                recur(node.right, Num())
                return Num()
            recur(node.left, union_type)
            recur(node.right, union_type)
            return union_type
        elif operator == 'Mod':
            union_type = Union(Num(), Str())
            left_probe = probe(node.left)
            right_probe = probe(node.right)
            if isinstance(left_probe, Str) or isinstance(right_probe, Str):
                recur(node.left, Str())
                recur(node.right, Str())
                return Str()
            if isinstance(left_probe, Num) or isinstance(right_probe, Num):
                recur(node.left, Num())
                recur(node.right, Num())
                return Num()
            recur(node.left, union_type)
            recur(node.right, union_type)
            return union_type
        else:
            recur(node.left, Num())
            recur(node.right, Num())
            return Num()
    if token == 'UnaryOp':
        if get_token(node.op) == 'Not':
            recur(node.operand, Bool())
            return Bool()
        else:
            recur(node.operand, Num())
            return Num()
    if token == 'Lambda':
        subtype = (expected_type.return_type
                   if isinstance(expected_type, Function) else Unknown())
        return_type = recur(node.body, subtype)
        return Function(Arguments(node.args, context), return_type)
    if token == 'IfExp':
        recur(node.test, Bool())
        #check_consistent_types(node, [node.body, node.orelse],
        #                       context, warnings)
        types = [recur(node.body, expected_type),
                 recur(node.orelse, expected_type)]
        return unify_types(types)
    if token == 'Dict':
        #check_consistent_types(node, node.keys, context, warnings)
        #check_consistent_types(node, node.values, context, warnings)
        key_type = unify_types([recur(key, Unknown()) for key in node.keys])
        value_type = unify_types([recur(value, Unknown())
                                  for value in node.values])
        return Dict(key_type, value_type)
    if token == 'Set':
        #check_consistent_types(node, node.elts, context, warnings)
        subtype = (expected_type.item_type if isinstance(expected_type, Set)
                   else Unknown())
        return Set(unify_types([recur(elt, Unknown()) for elt in node.elts]))
    if token == 'ListComp':
        subtype = (expected_type.item_type if isinstance(expected_type, List)
                   else Unknown())
        return List(comp(node.elt, node.generators, subtype))
    if token == 'SetComp':
        subtype = (expected_type.item_type if isinstance(expected_type, Set)
                   else Unknown())
        return Set(comp(node.elt, node.generators, subtype))
    if token == 'DictComp':
        expected_key_type = (expected_type.key_type
                             if isinstance(expected_type, Dict)
                             else Unknown())
        expected_value_type = (expected_type.value_type
                             if isinstance(expected_type, Dict)
                             else Unknown())
        key_type = comp(node.key, node.generators, expected_key_type)
        value_type = comp(node.value, node.generators, expected_value_type)
        return Dict(key_type, value_type)
    if token == 'GeneratorExp':
        subtype = (expected_type.item_type if isinstance(expected_type, List)
                   else Unknown())
        return List(comp(node.elt, node.generators, subtype))
    if token == 'Yield':
        return List(recur(node.value, Unkown()))
    if token == 'Compare':
        operator = get_token(node.ops[0])
        if len(node.ops) > 1 or len(node.comparators) > 1:
            warnings.warn(node, 'comparison-operator-chaining')
        if operator in ['Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE']:
            # all operands are constrained to have the same type
            # as their intersection
            exprs = [node.left] + node.comparators
            types = [probe(expr) for expr in exprs]
            intersection = reduce(type_intersection, types)
            for expr in exprs:
                recur(expr, intersection)
        if operator in ['Is', 'IsNot']:
            recur(node.left, Maybe(Unknown()))
            recur(node.comparators[0], NoneType())
        if operator in ['In', 'NotIn']:
            # constrain right to list/set of left, and left to instance of right
            left_probe = probe(node.left)
            right_probe = probe(node.comparators[0])
            union_type = Union(List(left_probe), Set(left_probe),
                               Dict(left_probe, Unknown()))
            recur(node.comparators[0], union_type)
            if isinstance(right_probe, (List, Set)):
                result = recur(node.left, right_probe.item_type)
            if isinstance(right_probe, Dict):
                recur(node.left, right_probe.key_type)
        return Bool()
    if token == 'Call':
        function_type = recur(node.func, Unknown())
        if not isinstance(function_type, (Class, Function)):
            warnings.warn(node, 'not-a-function')
            return Unknown()
        arg_types = function_type.arguments.types
        # TODO: handle keyword arguments

        argtypes, kwargtypes = call_argtypes(node, context)
        # make sure all required arguments are specified
        minargs = function_type.arguments.min_count
        required_kwargs = function_type.arguments.names[len(argtypes):minargs]
        missing = [name for name in required_kwargs if name not in kwargtypes]
        for missing_argument in missing:
            warnings.warn(node, 'missing-argument', missing_argument)
        if function_type.arguments.vararg_name is None:
            if len(argtypes) > len(function_type.arguments.types):
                warnings.warn(node, 'too-many-arguments')
        defined_argtypes = argtypes[:len(function_type.arguments.types)]
        for i, argtype in enumerate(defined_argtypes):
            deftype = function_type.arguments.types[i]
            check_argument_type(node, i + 1, argtype, [deftype], warnings)
        for name, kwargtype in kwargtypes.items():
            if name == '*args':
                if not isinstance(kwargtype, (Tuple, List)):
                    warnings.warn(node, 'invlaid-vararg-type')
            elif name == '**kwargs':
                if not isinstance(kwargtype, Dict):
                    warnings.warn(node, 'invalid-kwarg-type')
            else:
                deftype = function_type.arguments.get_dict().get(name)
                if deftype is None:
                    warnings.warn(node, 'extra-keyword', name)
                else:
                    check_argument_type(node, name, kwargtype, [deftype],
                                        warnings)


        for arg_expr, type_ in zip(node.args, arg_types):
            recur(arg_expr, type_)
        if node.starargs is not None:
            recur(node.starargs, List(Unknown()))
        if node.kwargs is not None:
            recur(node.kwargs, Dict(Unknown(), Unknown()))
        return function_type.return_type
    if token == 'Repr':
        return Str()
    if token == 'Num':
        return Num()
    if token == 'Str':
        return Str()
    if token == 'Attribute':
        value_type = recur(node.value, Unknown())
        if not isinstance(value_type, Instance):
            warnings.warn(node, 'not-an-instance')
            return Unknown()
        return value_type.attributes.get_type(node.attr) or Unknown()
    if token == 'Subscript':
        union_type = Union(List(Unknown()), Dict(Unknown(), Unknown()),
                           BaseTuple())
        value_type = recur(node.value, union_type)
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
        elif get_token(node.slice) == 'Slice':
            if node.slice.lower is not None:
                recur(node.slice.lower, Num())
            if node.slice.upper is not None:
                recur(node.slice.upper, Num())
            if node.slice.step is not None:
                recur(node.slice.step, Num())
            return value_type
        else:
            return value_type
    if token == 'Name':
        defined_type = context.get_type(node.id)
        if defined_type is None:
            warnings.warn(node, 'undefined', node.id)
        context.add_constraint(node.id, expected_type)
        return defined_type or Unknown()
    if token == 'List':
        # find intersection of specified types,
        #intersect = check_consistent_types(node, node.elts, context, warnings)
        subtype = (expected_type.item_type if isinstance(expected_type, List)
                   else Unknown())
        return List(unify_types([recur(elt, subtype) for elt in node.elts]))
    if token == 'Tuple':
        if (isinstance(expected_type, Tuple)
                and len(node.elts) == len(expected_type.item_types)):
            return Tuple([recur(element, type_) for element, type_ in
                          zip(node.elts, expected_type.item_types)])
        return Tuple([recur(element, Unknown()) for element in node.elts])
    raise Exception('visit_expression does not recognize ' + token)


def expression_type(expr, context):
    return visit_expression(expr, Unknown(), context, NullWarnings())
