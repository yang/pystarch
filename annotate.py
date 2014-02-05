import sys
import ast
from itertools import izip
from operator import itemgetter
from main import Visitor


def add_annotation(line, offset, length, label):
    before = line[:offset]
    symbol = line[offset:(offset + length)]
    after = line[(offset + length):]
    return before + '<a href="{0}">{1}</a>'.format(label, symbol) + after


def annotate_line(line, annotations):
    # apply annotations from right to left so that offsets don't change
    for annotation in sorted(annotations, key=itemgetter(0), reverse=True):
        offset, length, label = annotation
        line = add_annotation(line, offset, length, label)
    return line


def group_by_line_number(annotations):
    grouped = {}
    for annotation in annotations:
        line_number, offset, length, label = annotation
        grouped.setdefault(line_number, []).append((offset, length, label))
    return grouped


def main():
    filepath = sys.argv[1]
    with open(filepath) as source_file:
        source = source_file.read()
    tree = ast.parse(source, filepath)
    visitor = Visitor(filepath)
    visitor.visit(tree)
    lines = source.splitlines()
    annotations = visitor.annotations()
    grouped = group_by_line_number(annotations)
    pairs = izip(lines, (grouped.get(i + 1, []) for i in range(len(lines))))
    output = '\n'.join([annotate_line(*x) for x in pairs])
    print('<pre>')
    print(output)
    print('</pre>')


if __name__ == '__main__':
    main()
