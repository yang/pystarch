import os
import sys
import ast
from imports import ModuleVisitor
from backend import Context


def builtin_context():
    filename = 'builtins.py'
    context = Context()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(this_dir, filename)) as builtins_file:
        source = builtins_file.read()
    analyze(source, filename, context)
    return context


def analyze(source, filepath=None, context=None, imported=[]):
    tree = ast.parse(source, filepath)
    visitor = ModuleVisitor(filepath, context or builtin_context(), imported)
    visitor.visit(tree)
    return visitor.report()


def analysis(source, filepath=None):
    scope, warnings, _ = analyze(source, filepath)
    warning_output = ''.join([str(warning) + '\n' for warning in warnings])
    scope_output = str(scope)
    separator = '\n' if warning_output and scope_output else ''
    return scope_output + separator + warning_output


def main():
    filepath = sys.argv[1]
    with open(filepath) as source_file:
        source = source_file.read()
    sys.stdout.write(analysis(source, filepath))


if __name__ == '__main__':
    main()
