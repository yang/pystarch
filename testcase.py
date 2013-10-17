import testimport

globe = 1

class MyClass(object):
    class_attr = 1
    def class_method(self, a):
        return a

    def another_method(self, b):
        return [2]


def my_function(sam, maxi):
    x = True
    alice = 1
    bob = 2
    bob = 2 + sam
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

a,b,c = [1,2,3]
a,b,c = 'abc'
a = [1,2,3]
a[:2]
c = b * 4
my_function()
instance = MyClass()
x = instance.class_attr
y = instance.another_method('a')

z = testimport.imported
with open('side_effect', 'w') as f:
    f.write('uh oh')
