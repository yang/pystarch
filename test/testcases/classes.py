

class Test:
    def __init__(self):
        self.x = 1
        self.y = '2'

    def f(self, a):
        return a + self.x


t = Test()
a = t.x
b = t.y
c = t.f(2)
