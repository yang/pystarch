def f(a):
    if a > 5:
        return 2 * a
    else:
        return None
def g(a):
    if a > 5:
        return None
    else:
        return 2 * a
def h(a):
    return g(a) if a > 5 else None
a = f(3)
b = g(3)
c = h(3)
