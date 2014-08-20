from functools import partial
from context import Scope, Symbol
from type_objects import Bool, Num, Str, List, Tuple, Set, BaseTuple, \
    Dict, Function, Instance, Unknown, NoneType, Class, Union, Maybe
from evaluate import static_evaluate, UnknownValue
from util import unique_type, unify_types, type_intersection, type_subset
from assign import assign
from function import construct_function_type


def get_token(node):
    return node.__class__.__name__


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
            left_probe = probe(node.left)
            right_probe = probe(node.right)
            if isinstance(left_probe, Tuple) or isinstance(right_probe, Tuple):
                left = recur(node.left, BaseTuple())
                right = recur(node.right, BaseTuple())
                if isinstance(left, Tuple) and isinstance(right, Tuple):
                    return Tuple(left.item_types + right.item_types)
                else:
                    return Unknown()
            union_type = Union(Num(), Str(), List(Unknown()))
            left_intersect = type_intersection(left_probe, union_type)
            right_intersect = type_intersection(right_probe, union_type)
            intersect = type_intersection(left_intersect, right_intersect)
            if intersect is not None:
                recur(node.left, intersect)
                recur(node.right, intersect)
                return intersect
            elif left_intersect is not None:
                recur(node.left, left_intersect)
                recur(node.right, left_intersect)
                return left_intersect
            elif right_intersect is not None:
                recur(node.left, right_intersect)
                recur(node.right, right_intersect)
                return right_intersect
            else:
                recur(node.left, union_type)
                recur(node.right, union_type)
                return union_type
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
            # num % num OR str % unknown
            left_probe = probe(node.left)
            right_probe = probe(node.right)
            if (type_subset(Str(), left_probe) and
                    not type_subset(Num(), left_probe)):
                recur(node.left, Str())
                recur(node.right, Unknown())
                return Str()
            if (type_subset(Num(), left_probe) and
                    not type_subset(Str(), left_probe)):
                recur(node.left, Num())
                recur(node.right, Num())
                return Num()
            union_type = Union(Num(), Str())
            recur(node.left, union_type)
            recur(node.right, Unknown())
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
        return construct_function_type(node, LambdaVisitor(context))
    if token == 'IfExp':
        recur(node.test, Bool())
        types = [recur(node.body, expected_type),
                 recur(node.orelse, expected_type)]
        return unify_types(types)
    if token == 'Dict':
        key_type = unify_types([recur(key, Unknown()) for key in node.keys])
        value_type = unify_types([recur(value, Unknown())
                                  for value in node.values])
        return Dict(key_type, value_type)
    if token == 'Set':
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
        return List(recur(node.value, Unknown()))
    if token == 'Compare':
        operator = get_token(node.ops[0])
        if len(node.ops) > 1 or len(node.comparators) > 1:
            warnings.warn(node, 'comparison-operator-chaining')
        if operator in ['Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE']:
            # all operands are constrained to have the same type
            # as their intersection
            left_probe = probe(node.left)
            right_probe = probe(node.comparators[0])
            intersection = type_intersection(left_probe, right_probe)
            if intersection is None:
                recur(node.left, right_probe)
                recur(node.comparators[0], left_probe)
            else:
                recur(node.left, intersection)
                recur(node.comparators[0], intersection)
        if operator in ['Is', 'IsNot']:
            recur(node.left, Maybe(Unknown()))
            recur(node.comparators[0], NoneType())
        if operator in ['In', 'NotIn']:
            # constrain right to list/set of left, and left to inst. of right
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
            if not isinstance(function_type, Unknown):
                warnings.warn(node, 'not-a-function')
            return Unknown()
        signature = function_type.signature
        instance = (function_type.instance
                    if isinstance(function_type, Function) else None)
        offset = 1 if (instance is not None
                       or isinstance(function_type, Class)) else 0

        argument_scope = Scope()
        if instance is not None:
            self_symbol = Symbol(signature.names[0], instance)
            argument_scope.add(self_symbol)

        # make sure all required arguments are specified
        if node.starargs is None and node.kwargs is None:
            start = offset + len(node.args)
            required = signature.names[start:signature.min_count]
            kwarg_names = [keyword.arg for keyword in node.keywords]
            missing = [name for name in required if name not in kwarg_names]
            for missing_argument in missing:
                warnings.warn(node, 'missing-argument', missing_argument)

        # check for too many arguments
        if signature.vararg_name is None:
            if len(node.args) + len(node.keywords) > len(signature.types):
                warnings.warn(node, 'too-many-arguments')

        # load positional arguments
        for i, arg in enumerate(node.args):
            if i + offset >= len(signature):
                break
            arg_type = recur(arg, signature.types[i + offset])
            value = static_evaluate(arg, context)
            argument_scope.add(Symbol(signature.names[i + offset],
                                      arg_type, value))

        # load keyword arguments
        for kwarg in node.keywords:
            # TODO: make sure there is no overlap with positional args
            expected_type = signature.get_dict().get(kwarg.arg)
            if expected_type is None:
                warnings.warn(node, 'extra-keyword', kwarg.arg)
            else:
                arg_type = recur(kwarg.value, expected_type)
                value = static_evaluate(kwarg.value, context)
                argument_scope.add(Symbol(kwarg.arg, arg_type, value))

        if node.starargs is not None:
            recur(node.starargs, List(Unknown()))
        if node.kwargs is not None:
            recur(node.kwargs, Dict(Unknown(), Unknown()))

        return_type, _ = function_type.evaluator.evaluate(argument_scope)
        return return_type
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


class LambdaVisitor(object):
    def __init__(self, context):
        self._context = context

    def clone(self):
        return self

    def context(self):
        return self._context

    def visit(self, expression):
        result_type = expression_type(expression, self._context)
        symbol = Symbol('', result_type)
        self._context.set_return(symbol)

    def begin_scope(self):
        self._context.begin_scope()

    def end_scope(self):
        return self._context.end_scope()

    def merge_scope(self, scope):
        self._context.merge_scope(scope)


def expression_type(expr, context):
    return visit_expression(expr, Unknown(), context, NullWarnings())
