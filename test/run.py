import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import analysis
from difflib import unified_diff


def main():
    filenames = os.listdir('testcases')
    python_filenames = [x for x in filenames if x.endswith('.py')]
    for filename in python_filenames:
        name, _ = os.path.splitext(filename)
        filepath = os.path.join('testcases', filename)
        golden_path = os.path.join('golden', name + '.out')
        if not os.path.exists(golden_path):
            print(name + ': MISSING GOLDEN FILE')
            continue
        with open(filepath) as source_file:
            source = source_file.read()
        output = analysis(source, filepath)
        with open(golden_path) as golden_file:
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
