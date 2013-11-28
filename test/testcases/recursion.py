

def f(a):
    return a * f(a - 1) if a > 1 else 1


x = f(5)
