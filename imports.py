import imp, marshal, dis, meta


def import_code(import_name):
    # TODO: find_module does not support heirarchical module names
    module_file, module_path, _ = imp.find_module(import_name)
    if module_file is None:
        raise RuntimeError('Could not find module source for ' + import_name)
    data = module_file.read()
    module_file.close()
    if module_path.endswith('.py'):
        return data
    code_section = data[8:]
    code = marshal.load(code_section)
    return meta.dump_python_source(meta.decompile(code))


def unit_test():
    print import_code('re')


if __name__ == '__main__':
    unit_test()
