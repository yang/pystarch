import sys, os, imp, marshal, meta


def pyc_source(pyc_contents):
    code_section = pyc_contents[8:]
    code = marshal.load(code_section)
    return meta.dump_python_source(meta.decompile(code))


def get_module_source_path(import_name, paths=[]):
    python_paths = paths + sys.path[1:]  # sys.path includes PYTHONPATH env var
    try:
        module_file, module_path, _ = imp.find_module(import_name, python_paths)
        print(import_name + ' => ' + module_path)
    except ImportError:
        raise RuntimeError('Could not find module for ' + import_name)
    if module_file:
        module_file.close()
    if module_file is None and module_path == '':
        # module does not live in a file
        raise RuntimeError('Could not find module source for ' + import_name)
    elif module_file is None:   # probably a package
        if os.path.isdir(module_path):
            for extension in ['py', 'pyc', 'pyo']:
                filepath = os.path.join(module_path, '__init__.' + extension)
                if os.path.exists(filepath):
                    return filepath, True
            raise RuntimeError('Could not find __init__.py for '
                               + import_name)
        else:
            raise RuntimeError('Unrecognized module type')
    return module_path, False


def import_source(import_name, paths=[]):
    module_path, is_package = get_module_source_path(import_name, paths)
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


def unit_test():
    print import_source('re')


if __name__ == '__main__':
    unit_test()
