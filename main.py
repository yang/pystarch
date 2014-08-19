import os
import sys
import ast
import sys, os, imp, marshal, meta
import cPickle as pickle
from hashlib import sha256
from visitor import ScopeVisitor
from backend import Scope, Symbol, UnknownValue, Instance, Unknown, Context


NAME = 'strictpy'
__version__ = '1.0.0'


def pyc_source(pyc_contents):
    code_section = pyc_contents[8:]
    code = marshal.load(code_section)
    return meta.dump_python_source(meta.decompile(code))


def get_module_source_path(import_name, current_filepath):
    if import_name is None:
        module_file = None
        module_path = current_filepath
    else:
        source_dir = os.path.abspath(os.path.dirname(current_filepath))
        # sys.path includes PYTHONPATH env var
        python_paths = [source_dir] + sys.path[1:]
        try:
            module_file, module_path, _ = imp.find_module(
                import_name, python_paths)
            #print(import_name + ' => ' + module_path)
        except ImportError:
            raise RuntimeError('Could not find module for ' + import_name)
        if module_file:
            module_file.close()
    if module_file is None and module_path == '':
        # module does not live in a file
        raise RuntimeError('Could not find module source for '
            + str(import_name))
    elif module_file is None:   # probably a package
        if os.path.isdir(module_path):
            for extension in ['py', 'pyc', 'pyo']:
                filepath = os.path.join(module_path, '__init__.' + extension)
                if os.path.exists(filepath):
                    return filepath, True
            raise RuntimeError('Could not find __init__.py for '
                               + str(import_name))
        else:
            raise RuntimeError('Unrecognized module type')
    return module_path, False


def import_source(import_name, current_filepath):
    module_path, is_package = get_module_source_path(
        import_name, current_filepath)
    if module_path.endswith('.py'):
        with open(module_path) as module_file:
            return module_file.read(), module_path, is_package
    elif module_path.endswith(('.pyc', '.pyo')):
        py_path = module_path[:-1]  # look for ".py" file in same dir
        if os.path.exists(py_path):
            with open(py_path) as py_file:
                return py_file.read(), module_path, is_package
        else:
            with open(module_path) as module_file:
                return pyc_source(module_file.read()), module_path, is_package
    else:
        raise RuntimeError('Unrecognized extension: ' + module_path)


def import_module(name, current_filepath, imported):
    source, filepath, is_package = import_source(name, current_filepath)
    cache_filename = sha256(filepath + '~' + source).hexdigest()
    cache_filepath = os.path.join(os.sep, 'var', 'cache', NAME,
                                  __version__, cache_filename)

    if os.path.exists(cache_filepath):
        with open(cache_filepath, 'rb') as cache_file:
            return pickle.load(cache_file), filepath, is_package
    elif filepath in imported:
        i = imported.index(filepath)
        paths = ' -> '.join(imported[i:] + [filepath])
        #print('CIRCULAR: ' + paths)
        return Instance('object', Scope()), filepath, is_package
    else:
        imported.append(filepath)
        scope, _, _ = analyze(source, filepath, imported=imported)
        module = Instance('object', scope)
        with open(cache_filepath, 'wb') as cache_file:
            pickle.dump(module, cache_file, pickle.HIGHEST_PROTOCOL)
        return module, filepath, is_package


def import_chain(fully_qualified_name, asname, import_scope, current_filepath,
        imported):
    scope = import_scope
    filepath = current_filepath
    is_package = True
    names = fully_qualified_name.split('.') if fully_qualified_name else [None]
    for name in names:
        if scope is None:
            raise RuntimeError('Cannot import ' + fully_qualified_name)
        if is_package:
            import_type, filepath, is_package = import_module(
                name, filepath, imported)
            if asname is None:
                scope.add(Symbol(name, import_type, UnknownValue()))
            scope = import_type.attributes
        else:
            import_type = scope.get_type(name)
            scope = None
    if asname is not None:
        import_scope.add(Symbol(asname, import_type, UnknownValue()))
    return import_type


def get_path_for_level(filepath, level):
    for _ in range(level):
        filepath = os.path.dirname(filepath)
    if level > 0:
        filepath = os.path.join(filepath, '__init__.py')
    return filepath


# only for "from x import y" syntax
def import_from_chain(fully_qualified_name, level, current_filepath, imported):
    return import_chain(fully_qualified_name, None, Scope(),
        get_path_for_level(current_filepath, level), imported)


class ModuleVisitor(ScopeVisitor):

    def visit_Module(self, node):
        self.begin_scope()
        self.generic_visit(node)
        # don't end scope so that caller can see what is in the scope

    def visit_Import(self, node):
        scope = self._context.get_top_scope()
        for alias in node.names:
            try:
                import_chain(alias.name, alias.asname, scope, self._filepath,
                    self._imported)
            except RuntimeError as failure:
                self.warn('import-failed', node,
                          alias.name + ': ' + str(failure))

    def visit_ImportFrom(self, node):
        try:
            module = import_from_chain(node.module, node.level, self._filepath,
                self._imported)
        except RuntimeError as failure:
            self.warn('import-failed', node, '{0}: {1}'.format(
                node.module, failure))
            return
        if not isinstance(module, Instance):
            self.warn('invalid-import', node, node.module)
            return

        for alias in node.names:
            symbol_name = alias.asname or alias.name
            symbol_type = module.attributes.get_type(alias.name) or Unknown()
            self._context.add(Symbol(symbol_name, symbol_type, UnknownValue()))


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
    warning_output = str(warnings)
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
