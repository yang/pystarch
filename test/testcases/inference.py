
x = 5 if random() > 0.5 else None
y = 2 if random() > 0.2 else None

if x is None or y is None:
    z = x + y
else:
    z = x * y


a = x + 1 if x is not None or y is not None else 1
b = x + 1 if x is not None and y is not None else 1
