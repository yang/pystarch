

def f(a, b, c, d=1, e='x', f=None, *args, **kwargs):
    return []


f()
f(1,2)
f(1,2, c=3)
f(1,2, p=3)
f(a=1, b=2, c=3)
f(1,2,3)
f(1,2,3, e=4)
f(1,2,3, e='y')
