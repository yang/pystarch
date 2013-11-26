from functools import partial
from type_objects import Any, NoneType, Bool, Num, Str, List, Tuple, Set, \
    Dict, Function, Instance, Class, Undefined


def get_token(node):
    return node.__class__.__name__


# adds assigned symbols to the current namespace, does not do validation
def assign(target, value, context, generator=False):
    value_type = expression_type(value, context)
    if generator:
        if hasattr(value_type, 'item_type'):
            assign_type = value_type.item_type
        elif (hasattr(value_type, 'item_types')
                and len(value_type.item_types) > 0):
            # assume that all elements have the same type
            assign_type = value_type.item_types[0]
        else:
            raise TypeError('Invalid type in generator')
    else:
        assign_type = value_type

    target_token = get_token(target)
    if target_token in ('Tuple', 'List'):
        if isinstance(assign_type, Tuple):
            if len(target.elts) != len(assign_type.item_types):
                raise ValueError('Tuple unpacking length mismatch')
            assignments = [(element.id, item_type) for element, item_type
                in zip(target.elts, assign_type.item_types)]
        elif isinstance(assign_type, List):
            element_type = assign_type.item_type
            assignments = [(element.id, element_type)
                for element in target.elts]
        else:
            raise TypeError('Invalid value type in assignment')
    elif target_token == 'Name':
        assignments = [(target.id, assign_type)]
    else:
        raise RuntimeError('Unrecognized assignment target ' + target_token)

    for name, assigned_type in assignments:
        context.add_symbol(name, assigned_type)
    return assignments


def comprehension_type(elements, generators, context):
    context.begin_namespace()
    for generator in generators:
        item_type = expression_type(generator.iter, context)
        assign(generator.target, generator.iter, context, generator=True)
    element_types = [expression_type(element, context) for element in elements]
    context.end_namespace()
    return element_types


# Note: "True" and "False" evalute to Bool because they are symbol
# names that have their types builtin to the default context. Similarly,
# "None" has type NoneType.
def expression_type(node, context):
    """
    This function determines the type of an expression, but does
    not do any type validation.
    """
    recur = partial(expression_type, context=context)
    token = get_token(node)
    if token == 'BoolOp':
        return recur(node.values[0])
    if token == 'BinOp':
        if get_token(node.op) in ['Add', 'Mult']:
            if Str() in [recur(node.left), recur(node.right)]:
                return Str()
        return Num()
    if token == 'UnaryOp':
        if get_token(node.op) == 'Not':
            return Bool()
        else:
            return Num()
    if token == 'Lambda':
        # TODO: enter arguments
        arguments = None
        return Function(arguments, recur(node.body))
    if token == 'IfExp':
        return recur(node.body)
    if token == 'Dict':
        return Dict(recur(node.keys[0]), recur(node.values[0]))
    if token == 'Set':
        return Set(recur(node.elts[0]))
    if token == 'ListComp':
        element_type, = comprehension_type([node.elt], node.generators, context)
        return List(element_type)
    if token == 'SetComp':
        element_type, = comprehension_type([node.elt], node.generators, context)
        return Set(element_type)
    if token == 'DictComp':
        key_type, value_type = comprehension_type([node.key, node.value],
            node.generators, context)
        return Dict(key_type, value_type)
    if token == 'GeneratorExp':
        element_type, = comprehension_type([node.elt], node.generators, context)
        return List(element_type)
    if token == 'Yield':
        return recur(node.value)
    if token == 'Compare':
        return Bool()
    if token == 'Call':
        return recur(node.func).return_type
    if token == 'Repr':    # TODO: is Repr a Str?
        return Str()
    if token == 'Num':
        return Num()
    if token == 'Str':
        return Str()
    if token == 'Attribute':
        return context.get_attr_type(recur(node.value), node.attr)
    if token == 'Subscript':
        return recur(node.value)
    if token == 'Name':
        return context.get_type(node.id, Undefined())
    if token == 'List':
        return (List(recur(node.elts[0])) if len(node.elts) > 0
            else List(NoneType()))
    if token == 'Tuple':
        item_types = [recur(e) for e in node.elts]
        return Tuple(item_types)
    raise Exception('evalute_type does not recognize ' + token)


def unit_test():
    context = Context()
    source = [
        '5 + 5',
        'not True',
        '+"abc"',
        '[a for a in (1, 2, 3)]',
        '[a for a in [1, 2, 3]]',
        '[a for a in {1, 2, 3}]',
        '[a * "a" for a in [1, 2, 3]]',
        '[{0: "a" * (a + 1)} for a in [1, 2, 3]]',
        '{a: b for a, b in [("x", 0), ("y", 1)]}',
    ]
    module = ast.parse('\n'.join(source))
    print(ast.dump(module))
    for i, statement in enumerate(module.body):
        expression = statement.value
        print(source[i] + ': ' + str(expression_type(expression, context)))


if __name__ == '__main__':
    import ast
    from context import Context
    unit_test()
