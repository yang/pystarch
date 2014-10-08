PyStarch
========
PyStarch is a lint-style command line tool for static type checking of Python programs. It also checks that programs conform to certain constraints that are intended to encourage a more functional programming style.

You can think of PyStarch as defining a sub-language of Python that lies halfway between Python and Haskell, combining the simple syntax of Python with the safety and cleanliness of Haskell. Although PyStarch provides warnings to encourage you to use this sub-language (such as warning when variables are reassigned), you can choose to ignore any warnings you want since your code still runs in the standard Python interpreter.


Does Python need static analysis?
=================================
I've heard some Python developers argue that they don't need static analysis because they have lots of unit tests. Static analysis tools essentially run thousands of additional unit tests on your code for free. Unlike manually written unit tests, the static analysis tool's unit tests are generated automatically (requiring no developer time), are bug-free (requiring no debugging or maintenance), and have complete code coverage (so you don't have to run a code coverage tool on them).

The only reasonable argument against using static analysis is that it may require a bit more time upfront to structure your code in a way that is amenable to static analysis. But I've generally found that this tends to produce cleaner, more readable code, so it is probably a good idea anyways, unless you are writing a quick throwaway prototype perhaps.


Type Checking
=============
You can't add "None" to an integer, so PyStarch generates a warning if you try it.

    x = 1 + None
    ---
    x Num
    example.py:1 type-error "None" (NoneType vs Num)


Constraints
===========
The types of function arguments are inferred by the constraints imposed by the way they are used in the body of the function.

    def f(a, b):
        return len(a * b)
    x = f(2, 2)
    ---
    f Function(a: Str, b: Num -> Num)
    x Num
    example.py:3 type-error "Num" (Num vs Str)

Note that PyStarch assumes that when multiplying a string by an integer the integer is on the right hand side. An error is generated because the arguments passed to "f" don't match the inferred type signature.


Maybe Inference
===============
As in Haskell, expressions can take on a "Maybe" type if they might be None or some non-None value.

    from random import random
    a = 1 if random() > 0.5 else None
    b = 1 if random() > 0.5 else None
    c = a + b if a is not None and b is not None else None
    d = a + b if a is not None or b is not None else None
    ---
    a Maybe(Num)
    b Maybe(Num)
    c Maybe(Num)
    d Maybe(Num)
    random Unknown
    example.py:5 type-error "a" (Maybe(Num) vs Num)
    example.py:5 type-error "b" (Maybe(Num) vs Num)

Notice that the line defining "c" does not generate an error because it can be deduced that the addition only takes place when both operands are not None, but on the line defining "d" the same cannot be deduced so it generates an error.

Installation and Usage
======================
    sudo pip install meta
    git clone https://github.com/clark800/pystarch.git
    cd pystarch
    python2.7 main.py module-to-analyze.py

This will produce a listing of the types of all the symbols in the module's top scope, followed by a list of all the warnings generated while analyzing the module.
