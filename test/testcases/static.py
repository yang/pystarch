x01 = 1
x02 = x01 + 2
x03 = False
x04 = x03 and True
x05 = x04 or True


def f(x):
    if True:
        return 2 + x
    else:
        return None

x06 = f(1)
x07 = x06 is not None

if x06 is not None:
    x08 = x06 + 2
else:
    x08 = x06 + 3
