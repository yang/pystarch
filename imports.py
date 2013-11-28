import os, imp, marshal, meta


def pyc_source(pyc_contents):
    code_section = pyc_contents[8:]
    code = marshal.load(code_section)
    return meta.dump_python_source(meta.decompile(code))


def import_source(import_name, paths=None):
    # TODO: find_module does not support heirarchical module names
    module_file, module_path, _ = imp.find_module(import_name, paths)
    if module_file is None:
        raise RuntimeError('Could not find module source for ' + import_name)
    if module_path.endswith('.py'):
        source = module_file.read()
        module_file.close()
        return source, module_path
    elif module_path.endswith(('.pyc', '.pyo')):
        py_path = module_path[:-1]
        if os.path.exists(py_path):
            module_file.close()
            with open(py_path) as py_file:
                source = py_file.read()
            return source, module_path
        else:
            data = module_file.read()
            module_file.close()
            return pyc_source(data), module_path
    else:
        raise RuntimeError('Unrecognized extension: ' + module_path)


def unit_test():
    print import_source('re')


if __name__ == '__main__':
    unit_test()
