from functools import partial
from type_objects import Any, NoneType, Bool, Num, Str, List, Tuple, Set, \
    Dict, Function, Instance, Class, Undefined


def get_token(node):
    return node.__class__.__name__


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
        if get_token(node.op) in ['Add', 'Mul']:
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
        return List(recur(node.elt))
    if token == 'SetComp':
        return Set(recur(node.elt))
    if token == 'DictComp':
        return Dict(recur(node.key), recur(node.value))
    if token == 'GeneratorExp':
        return Tuple(recur(node.elt))
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
        return context.get_type(node.id, Undefined)
    if token == 'List':
        return List(recur(node.elts[0]))
    if token == 'Tuple':
        return Tuple(recur(node.elts[0]))
    raise Exception('evalute_type does not recognize ' + token)


def unit_test():
    context = Context()
    source = [
        '5 + 5',
        'not True',
        '+"abc"'
    ]
    module = ast.parse('\n'.join(source))
    #print(ast.dump(module))
    for i, statement in enumerate(module.body):
        expression = statement.value
        print(source[i] + ': ' + str(expression_type(expression, context)))


if __name__ == '__main__':
    import ast
    from context import Context
    unit_test()
