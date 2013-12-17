import ast


class Visitor(ast.NodeVisitor):
    def __init__(self):
        ast.NodeVisitor.__init__(self)
        self.names = []

    def visit_Name(self, node):
        self.names.append(node.id)


def get_names(node):
    visitor = Visitor()
    visitor.visit(node)
    return visitor.names
