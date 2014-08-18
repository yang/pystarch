import expr
from itertools import chain, repeat
from context import Symbol
from evaluate import static_evaluate, UnknownValue
from type_objects import Unknown, List, Set, Tuple, Instance


def assign_single_target(target, assigned_type, static_value, context):
    target_token = expr.get_token(target)
    if target_token == 'Name':
        old_symbol = context.get(target.id)
        new_symbol = Symbol(target.id, assigned_type, static_value)
        context.add(new_symbol)
        return (target.id, old_symbol, new_symbol)
    elif target_token == 'Subscript':
        value = expr.expression_type(target.value, context)
        # TODO: implement this
        return ('Subscript', None, None)
    elif target_token == 'Attribute':
        instance = expr.expression_type(target.value, context)
        if not isinstance(instance, Instance):
            return (target.attr, None, None)
        old_symbol = instance.attributes.get(target.attr)
        new_symbol = Symbol(target.attr, assigned_type, static_value)
        instance.attributes.add(new_symbol)
        return (target.attr, old_symbol, new_symbol)
    else:
        raise RuntimeError('Unrecognized assignment target: ' + target_token)


# returns a list of assignments that were made [(name, old_symbol, new_symbol)]
# so that the validator can produce warnings if necessary
def assign(target, value, context, generator=False):
    value_type = expr.expression_type(value, context)
    static_value = static_evaluate(value, context)
    if generator:
        if isinstance(value_type, (List, Set)):
            assign_type = value_type.item_type
        elif isinstance(value_type, Tuple):
            return []       # TODO
        else:
            return []
    else:
        assign_type = value_type

    target_token = expr.get_token(target)
    if target_token in ('Tuple', 'List'):
        values = static_value if isinstance(static_value,
                                            (Tuple, List)) else []
        assign_values = chain(values, repeat(UnknownValue()))
        if isinstance(assign_type, Tuple):
            assign_types = chain(assign_type.item_types, repeat(Unknown()))
        elif isinstance(assign_type, (List, Set)):
            assign_types = repeat(assign_type.item_type)
        else:
            assign_types = repeat(Unknown())
        return [assign_single_target(target, assign_type, static_value,
                context) for target, assign_type, static_value
                in zip(target.elts, assign_types, assign_values)]
    else:
        return [assign_single_target(target, assign_type,
                                     static_value, context)]
