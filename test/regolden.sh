#!/bin/bash
for path in testcases/*.py
do
    filename=$(basename $path)
    golden=${filename%.*}.out
    python2 ../main.py $path > golden/$golden
done
