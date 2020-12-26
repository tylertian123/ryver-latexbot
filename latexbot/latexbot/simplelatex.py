r"""
Convert simple, easy-to-read math expressions into LaTeX.

E.g. `sin(sqrt(e^x + a) / 2)` becomes `\sin \left(\frac{\sqrt{e^{x}+a}}{2}\right)`.
"""

import lark
import typing


GRAMMAR = r"""
%import common.WS
%import common.NUMBER
%ignore WS

VARIABLE: /\.\.\.|inf|oo|[a-zA-Z]+|(\\\w+)/

VAL_SUFFIX: /!|'+/

ARW_OP: /<->|<=>|<-->|<==>|<--|-->|<==|==>|<-|->|<<=|=>/
CMP_OP: /<=|>=|!=|[<>=]/
SUM_OP: /[+-]/
MUL_OP: /[\*\/%]/
POW_OP: /\^|\*\*/

FUNC_NAME.2: /".+?"/
           | "sin" | "cos" | "tan" | "sinh" | "cosh" | "tanh"
           | "arctan2" | "arcsin" | "arccos" | "arctan" | "arcsinh" | "arccosh" | "arctanh"
           | "atan2" | "asin" | "acos" | "atan" | "asinh" | "acosh" | "atanh"
           | "exp" | "log" | "ln" | "min" | "max" | "floor" | "ceil"

!func_modifier: POW_OP
              | "_"

ROOT.3: "sqrt" | "cbrt"

BIG_SYMB.3: "int" | "iint" | "iiint" | "iiiint" | "oint" | "sum" | "prod" | "lim"

LATEX: /\$.+?\$/

// Values that can be on the right-hand side of an implicit multiplication
?mvalue: VARIABLE             -> val
       | bvalue
       | mvalue VAL_SUFFIX    -> suffix
       | mvalue POW_OP value  -> op
       | VARIABLE NUMBER      -> sub
       | mvalue "_" value     -> sub

// Values that cannot be on the right-hand side of an implicit multiplication
?nmvalue: NUMBER               -> val
        | SUM_OP value         -> signed_val
        | nmvalue VAL_SUFFIX   -> suffix
        | nmvalue POW_OP value -> op
        | nmvalue "_" value    -> sub

// Values that are grouped together with brackets, absolute values, etc.
?bvalue.2: LATEX                                                                                    -> raw_latex
         | "(" operation ")"?                                                                       -> bracket
         | "[" operation "]"?                                                                       -> sbracket
         | "{" operation "}"?                                                                       -> cbracket
         | "|" operation "|"                                                                        -> abs
         | FUNC_NAME [func_modifier value [func_modifier value]] value                              -> func
         | FUNC_NAME [func_modifier value [func_modifier value]] "(" operation ("," operation)+ ")" -> func_bracket
         | BIG_SYMB [func_modifier value [func_modifier value]] value                               -> big_symb
         | BIG_SYMB [func_modifier value [func_modifier value]]                                     -> big_symb
         | ROOT value                                                                               -> root
         | "root" "[" operation "]" value                                                           -> nth_root

?value: mvalue
      | nmvalue

?mul_op: value
       | mul_op MUL_OP value -> op
       | mul_op mvalue       -> mul

?operation: mul_op
          | operation ARW_OP mul_op -> op
          | operation CMP_OP mul_op -> op
          | operation SUM_OP mul_op -> op

?start: operation
"""

SPECIAL_FUNCS = {
    "asin": "\\arcsin",
    "acos": "\\arccos",
    "atan": "\\arctan",
    "asinh": "\\arcsinh",
    "acosh": "\\arccosh",
    "atanh": "\\arctanh",
    "atan2": "\\operatorname{arctan2}",
    "arctan2": "\\operatorname{arctan2}",
    "floor": "\\operatorname{floor}",
    "ceil": "\\operatorname{ceil}",
}


SPECIAL_OPS = {
    "**": "^",
    "*": "\\cdot ",
    "%": "\\bmod ",
    ">=": "\\geq ",
    "<=": "\\leq ",
    "!=": "\\neq ",
    "->": "\\rightarrow ",
    "<-": "\\leftarrow ",
    "=>": "\\Rightarrow ",
    "<<=": "\\Leftarrow ",
    "<->": "\\leftrightarrow ",
    "<=>": "\\Leftrightarrow ",
    "-->": "\\longrightarrow ",
    "<--": "\\longleftarrow ",
    "==>": "\\Longrightarrow ",
    "<==": "\\Longleftarrow ",
    "<-->": "\\longleftrightarrow ",
    "<==>": "\\Longleftrightarrow ",
}


SPECIAL_SYMBS = {
    "inf": "\\infty ",
    "oo": "\\infty ",
    "...": "\\ldots ",
}


def strip_bracket(tree: lark.Tree) -> str:
    """
    Convert a parse tree into LaTeX and strip the outermost set of brackets if there is one.
    """
    if tree.data in ("bracket", "sbracket", "cbracket"):
        return tree_to_latex(tree.children[0])
    else:
        return tree_to_latex(tree)


def op_tree_to_latex(tree: lark.Tree) -> str:
    """
    Convert a tree with top level op (operator) into LaTeX.
    """
    tree.children[1] = SPECIAL_OPS.get(tree.children[1]) or tree.children[1]
    if tree.children[1] == "^":
        return f"{tree_to_latex(tree.children[0])}^{{{strip_bracket(tree.children[2])}}}"
    elif tree.children[1] == "/":
        return f"\\frac{{{strip_bracket(tree.children[0])}}}{{{strip_bracket(tree.children[2])}}}"
    else:
        return tree_to_latex(tree.children[0]) + tree.children[1] + tree_to_latex(tree.children[2])


def get_modifiers(tree: lark.Tree) -> typing.Tuple[str, str, int]:
    """
    Get the superscript and subscript for a function or other thing.
    """
    m1 = None
    m2 = None
    arg_start = 2
    if tree.children[1] is not None:
        m1 = f"{tree_to_latex(tree.children[1])}{{{strip_bracket(tree.children[2])}}}"
        arg_start = 4
        if tree.children[3] is not None:
            m2 = f"{tree_to_latex(tree.children[3])}{{{strip_bracket(tree.children[4])}}}"
            arg_start = 5
    return m1, m2, arg_start


def func_tree_to_latex(tree: lark.Tree, bracket: bool) -> str:
    """
    Convert a tree with top level func into LaTeX.
    """
    if tree.children[0].startswith("\"") and tree.children[0].endswith("\""):
        func = f"\\operatorname{{{tree.children[0][1:-1]}}}"
    else:
        func = SPECIAL_FUNCS.get(tree.children[0], "\\" + tree.children[0])
    m1, m2, arg_start = get_modifiers(tree)
    if m1:
        func += m1
    if m2:
        func += m2
    if bracket:
        func += f"\\left({','.join(tree_to_latex(c) for c in tree.children[arg_start:])}\\right)"
    else:
        func += f" {tree_to_latex(tree.children[arg_start])}"
    return func


def root_tree_to_latex(tree: lark.Tree) -> str:
    """
    Convert a tree with top level root into LaTeX.
    """
    expr = "\\sqrt"
    if tree.children[0] == "cbrt":
        expr += "[3]"
    return f"{expr}{{{strip_bracket(tree.children[1])}}}"


def big_symb_tree_to_latex(tree: lark.Tree) -> str:
    """
    Convert a tree with top level big_symb (integral, limit, sum, product) into LaTeX.
    """
    expr = "\\" + tree.children[0]
    m1, m2, arg_start = get_modifiers(tree)
    if m1:
        expr += m1
    if m2:
        expr += m2
    if len(tree.children) > arg_start:
        expr += tree_to_latex(tree.children[arg_start])
    return expr


TREE_PROCESSORS = {
    "val": lambda t: SPECIAL_SYMBS.get(t.children[0], t.children[0]),
    "func_modifier": lambda t: t.children[0],
    "raw_latex": lambda t: t.children[0][1:-1],
    "suffix": lambda t: tree_to_latex(t.children[0]) + t.children[1],
    "signed_val": lambda t: t.children[0] + tree_to_latex(t.children[1]),
    "bracket": lambda t: f"\\left({strip_bracket(t.children[0])}\\right)",
    "sbracket": lambda t: f"\\left[{strip_bracket(t.children[0])}\\right]",
    "cbracket": lambda t: f"\\left\\{{{strip_bracket(t.children[0])}\\right\\}}",
    "abs": lambda t: f"\\left|{strip_bracket(t.children[0])}\\right|",
    "func": lambda t: func_tree_to_latex(t, False),
    "func_bracket": lambda t: func_tree_to_latex(t, True),
    "big_symb": big_symb_tree_to_latex,
    "root": root_tree_to_latex,
    "nth_root": lambda t: f"\\sqrt[{strip_bracket(t.children[0])}]{{{strip_bracket(t.children[1])}}}",
    "sub": lambda t: f"{tree_to_latex(t.children[0])}_{{{tree_to_latex(t.children[1])}}}",
    "mul": lambda t: ''.join(tree_to_latex(c) for c in t.children),
    "op": op_tree_to_latex,
}


def tree_to_latex(expr: typing.Union[lark.Tree, lark.Token]) -> str:
    """
    Convert a parse tree into LaTeX.
    """
    if isinstance(expr, lark.Token):
        return expr
    return TREE_PROCESSORS[expr.data](expr)


def str_to_latex(expr: str) -> str:
    r"""
    Convert simple, easy-to-read math expressions into LaTeX.

    E.g. `sin(sqrt(e^x + a) / 2)` becomes `\sin \left(\frac{\sqrt{e^{x}+a}}{2}\right)` in LaTeX.

    As you can see, the syntax for these expressions are designed to be very easy to read and enter compared
    to LaTeX. Most of the supported operations are pretty intuitive, such as entering a basic expression with
    brackets and arithmetic operations. Some things that may not be immediately obvious are outlined below.

    Divisions are automatically converted into fractions and will follow order of operations.
    Use brackets if you wish to make a large fraction, e.g. `(sinx+cos^2x)^2/(y+1)`.

    In expressions where brackets are unnecessary, such as fractions, powers, subscripts, etc, the outermost
    brackets will be stripped away if there is a pair. This means that in many cases you can add brackets to
    clarify exactly what you mean, without having those brackets clutter up the final output.

    The `%` operator is a modulo. The `**` operator can be used for exponentiation in place of `^`.
    There are also comparison operators, including `=`, `!=` (not equal), `>`, `<`, `>=` (greater than or
    equal to) and `<=` (less than or equal to).

    To do a function call, simply write out the function name and argument(s). Brackets are not necessary; e.g.
    both `sin x`, and `sin(x)` are valid. Common functions will be automatically recognized, e.g. sin, cos, log,
    etc. To use a custom function name, surround it with double quotes like `"func"(x)`. Function names will be
    rendered with a different font (`\operatorname` in LaTeX) compared to variables. You can also put powers and
    subscripts on them, e.g. `sin^2x`. Note that here because of order of operations only the 2 is in the power,
    and the x is left as the argument to sin.

    When implicitly multiplying a variable and a function, there needs to be a space between them. E.g. `x sinx`
    and not `xsinx`, as the latter will get parsed as a single variable. There does not need to be a space
    between the function name and its argument, even when not using brackets.

    To do a square root, cube root, or nth root use `sqrt x`, `cbrt x`, and `root[n] x` respectively.
    Note that these operations only take a single value! Use brackets if you want to take the root
    of an entire expression, e.g. `sqrt(1+1)`.

    To do an integral, limit, summation or product, use one of the following:
    - `int`, `iint`, `iiint`, `iiiint` - Integral, double integral, triple integral and quadruple integral
    - `oint` - Contour integral
    - `sum` - Summation
    - `prod` - Product
    The bounds can be specified with `_lower^upper`, e.g. `int_0^(x+1)` is an integral from 0 to x+1.

    There is also a list of various single- and double-length arrows, such as `->`, `==>`, and two-directional
    arrows such as `<->`. Note that the fat left arrow is `<<=` and not `<=`, because the latter is the
    less-than-or-equal-to sign.

    You can insert subscripts explicitly with `_`, e.g. `x_i`, or automatically by putting a number right
    after a letter, e.g. `x1`.

    You can use `inf` or `oo` for an infinity symbol and `...` for an ellipsis.

    Factorials (`!`), primes (`'`, `''`, ...) are also supported, along with square braces, curly braces and
    absolute values.

    To insert LaTeX directly into the output, surround it with $, e.g. `$\vec{v}$`.
    To insert a single LaTeX command directly into the output, enter it directly with the backslash,
    e.g. `sin\theta`.
    """
    return tree_to_latex(parser.parse(expr))


parser = lark.Lark(GRAMMAR, start="start", parser="earley", lexer="standard", maybe_placeholders=True)
