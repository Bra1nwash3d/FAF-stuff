

class A:
    def __init__(self):
        pass

    def migrate(self):
        self.x = self.__dict__.get('x', 'sldfjsdklf')

    def print(self):
        print(self.x)

a = A()
a.migrate()
a.print()
