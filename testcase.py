
globe = 1

def my_function():
    x = True
    alice = 1
    bob = 2
    globe = 3
    return alice + bob


def func2():
    if 4 == my_function():
        return 1
    if 'a' == my_function():
        return 2

def func():
    alice = 1
    if alice == 2:
        return []
    alice = 'a'
    return alice


def another_function():
    alice = 'hey'
    if alice == [1]:
        return 5
    if alice is None:
        return 1
    if alice == 'hello':
        return 6
    alice += ''
    alice += 2
    return None


my_function()
with open('side_effect', 'w') as f:
    f.write('uh oh')
