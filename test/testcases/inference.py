
x = 5 if random() > 0.5 else None
y = 2 if random() > 0.2 else None

if x is None or y is None:
    z = x + y
else:
    z = x * y
