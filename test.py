import os
from main import analysis
from difflib import unified_diff


def main():
    filenames = os.listdir('testcases')
    for filename in filenames:
        name, _ = os.path.splitext(filename)
        filepath = os.path.join('testcases', filename)
        with open(filepath) as source_file:
            source = source_file.read()
        output = analysis(source, filepath) + '\n'
        with open(os.path.join('golden', name + '.out')) as golden_file:
            golden_output = golden_file.read()
        if output == golden_output:
            print(name + ': PASSED')
        else:
            print(name + ': FAILED')
            diffs = unified_diff(golden_output.splitlines(),
                output.splitlines())
            for diff in diffs:
                print(diff)


if __name__ == '__main__':
    main()
