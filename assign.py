from show import get_token

# adds assigned symbols to the current namespace, does not do validation
def assign(target, value, context):
    target_token = get_token(target)
    if target_token in ('Tuple', 'List'):
        value_token = get_token(value)
        if value_token not in ('Tuple', 'List', 'GeneratorExp', 'ListComp'):
            raise TypeError('Invalid value type')
        assigned_type = expression_type(value, context).item_type
        assignments = [(e.id, assigned_type) for e in target.elts]
    elif target_token == 'Name':
        assignments = [(target.id, expression_type(value, context))]
    else:
        raise RuntimeError('Unrecognized assignment target ' + target_token)

    for name, assigned_type in assignments:
        context.add_symbol(name, assigned_type)
    return assignments
