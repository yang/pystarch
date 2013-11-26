

# adds assigned symbols to the current namespace, does not do validation
def assign(target, value, context):
    target_token = get_token(target)
    if target_token in ('Tuple', 'List'):
        value_token = get_token(value)
        if value_token not in ('Tuple', 'List', 'GeneratorExp', 'ListComp'):
            raise TypeError('Invalid value type')
        assignment_type = expression_type(value, context).item_type
        for element in target.elts:
            context.add_symbol(element.id, assignment_type)
    elif target_token == 'Name':
        assignment_type = expression_type(value, context)
        context.add_symbol(target.name, assignment_type)
    else:
        raise RuntimeError('Unrecognized assignment target ' + target_token)

