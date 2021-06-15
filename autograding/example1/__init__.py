import check50
import check50.c
import os.path
from os import path
import os
from pycparser import c_ast, parse_file, c_generator
import pycparser_fake_libc


class FuncDefVisitor(c_ast.NodeVisitor):
    def __init__(self, bodies):
        self.bodies = bodies
        self.generator = c_generator.CGenerator()

    def visit_FuncDef(self, node):
        self.bodies[node.decl.name] = self.generator.visit(node)


def get_functions(filename):
    fake_libc_arg = "-I" + pycparser_fake_libc.directory
    ast = parse_file(
        filename,
        use_cpp=True,
        cpp_path="/usr/local/opt/llvm/bin/clang",
        cpp_args=[r"-E", fake_libc_arg],
    )

    bodies = {}
    v = FuncDefVisitor(bodies)
    v.visit(ast)
    return bodies


def get_correct_output(qnum: int):
    with open(f"{os.path.dirname(__file__)}/data/output_{qnum}.txt") as f:
        return f.read()


def generate_q2_code():
    bodies = {}
    if path.exists("794902.c"):
        bodies = get_functions("794902.c")
    elif path.exists("794907.c"):
        bodies = get_functions("794907.c")
    else:
        raise FileNotFoundError

    with open("q2.c", "w") as f:
        for k, v in bodies.items():
            if "main" not in k:
                f.write(v)
        with open(f"{os.path.dirname(__file__)}/data/q2_driver.c") as f2:
            f.write(f2.read())


@check50.check()
def q1_compiles():
    """q1 compiles"""
    if path.exists("794901.c"):
        check50.c.compile("794901.c", exe_name="q1")
    elif path.exists("794904.c"):
        check50.c.compile("794904.c", exe_name="q1")
    else:
        raise FileNotFoundError


@check50.check(q1_compiles)
def q1_io():
    """prints a tree"""
    correct_output = ""
    if path.exists("794901.c"):
        correct_output = get_correct_output(794901)
    elif path.exists("794904.c"):
        correct_output = get_correct_output(794904)
    else:
        raise FileNotFoundError
    check50.run("./q1 <<< 4").stdout(correct_output, regex=False).exit(0)


@check50.check()
def q2_compiles():
    """q2 compiles"""
    generate_q2_code()
    check50.c.compile("q2.c")


## use some novel test case instead
@check50.check(q2_compiles)
def q2_io():
    """does secret math"""
    correct_output = ""
    if path.exists("794902.c"):
        correct_output = "8"
    elif path.exists("794907.c"):
        correct_output = "12"
    else:
        raise FileNotFoundError
    check50.run("./q2").stdout(correct_output, regex=False).exit(0)


@check50.check()
def q3_compiles():
    """q3 compiles"""
    bodies = get_functions("788765.c")
    with open("q3.c", "w") as f:
        for k, v in bodies.items():
            if "main" not in k:
                f.write(v)
        with open(f"{os.path.dirname(__file__)}/data/q3_driver.c") as f2:
            f.write(f2.read())

    check50.c.compile("q3.c")


@check50.check(q3_compiles)
def q3_io():
    """rescues bby"""
    check50.run("./q3").stdout("98,99,98,98,121,108,3,8,3,", regex=False).exit(0)
