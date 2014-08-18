

# 1. keep looping through and adding more constraints until no change
# 2. dynamically trigger constraint updates when new constraints appear
#       using a network of constraints

def f(a, b, c):
    d = a + b       # tricky: limit a and b to Num!!
    e = d - 4
    return e


def g(x):
    return -x

def h(x):
    return x + 1


def j(x):
    return x[0]
