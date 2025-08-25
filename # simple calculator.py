#!/usr/bin/env python3
"""
Python AST to safely evaluate expressions (no eval/exec or attributes)
"""

from __future__ import annotations
import ast
import math
from typing import Any, Dict, Callable

# ---------------- SAFE EVALUATOR ---------------- #

class SafeEval(ast.NodeVisitor):
    def __init__(self, names: Dict[str, Any], funcs: Dict[str, Callable[..., float]]):
        self.names = names
        self.funcs = funcs

    def visit_Expression(self, node):  # type: ignore[override]
        return self.visit(node.body)

    # Py<3.8
    def visit_Num(self, node):  # type: ignore[override]
        return node.n

    # Py3.8+
    def visit_Constant(self, node):  # type: ignore[override]
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numeric constants allowed.")

    def visit_Name(self, node):  # type: ignore[override]
        if node.id in self.names:
            return self.names[node.id]
        raise NameError(f"Unknown name: {node.id}")

    def visit_UnaryOp(self, node):  # type: ignore[override]
        v = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):  return +v
        if isinstance(node.op, ast.USub):  return -v
        raise ValueError("Unsupported unary operator.")

    def visit_BinOp(self, node):  # type: ignore[override]
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):       return left + right
        if isinstance(op, ast.Sub):       return left - right
        if isinstance(op, ast.Mult):      return left * right
        if isinstance(op, ast.Div):       return left / right
        if isinstance(op, ast.FloorDiv):  return left // right
        if isinstance(op, ast.Mod):       return left % right
        if isinstance(op, ast.Pow):       return left ** right
        raise ValueError("Unsupported binary operator.")

    def visit_Call(self, node):  # type: ignore[override]
        # Only allow simple function names, no attributes (e.g., math.sin is blocked)
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed.")
        fname = node.func.id
        if fname not in self.funcs:
            raise NameError(f"Unknown function: {fname}")
        if node.keywords:
            raise ValueError("Keyword arguments are not allowed.")
        args = [self.visit(a) for a in node.args]
        return self.funcs[fname](*args)

    def generic_visit(self, node):  # type: ignore[override]
        raise ValueError(f"Disallowed expression: {type(node).__name__}")

def safe_eval(expr: str, names: Dict[str, Any], funcs: Dict[str, Callable[..., float]]) -> float:
    expr = preprocess(expr)
    tree = ast.parse(expr, mode='eval')
    return SafeEval(names, funcs).visit(tree)

# ---------------- PREPROCESSING ---------------- #

def preprocess(expr: str) -> str:
    s = expr.strip()
    # Alias ^ to **
    s = s.replace("^", "**")
    # Alias ln(x) -> log(x) (natural log)
    s = s.replace("ln(", "log(").replace("LN(", "log(")

    # Case-insensitive references to ans/mem
    s = replace_name_case_insensitive(s, "ans")
    s = replace_name_case_insensitive(s, "mem")

    # Expand factorial postfix: 5! -> factorial(5), (3+2)! -> factorial((3+2)), ans! -> factorial(ans)
    s = expand_factorials(s)
    return s

def replace_name_case_insensitive(s: str, name: str) -> str:
    import re
    pattern = re.compile(rf"\b{name}\b", re.IGNORECASE)
    return pattern.sub(name, s)

def expand_factorials(s: str) -> str:
    import re
    # Matches: ( ... )!  OR  word!  OR  number!
    token = r"(?:\([^()]*\)|[A-Za-z_]\w*|\d+(?:\.\d+)?)"
    pattern = re.compile(rf"({token})!")
    # Apply repeatedly until no more replacements
    prev = None
    out = s
    while out != prev:
        prev = out
        out = pattern.sub(r"factorial(\1)", out)
    return out

# ---------------- TRIG MODE WRAPPERS ---------------- #

class TrigMode:
    def __init__(self, mode: str = "rad"):
        self.mode = mode  # 'rad' or 'deg'
    def set_mode(self, mode: str):
        m = mode.lower()
        if m not in ("rad", "deg"):
            raise ValueError("Mode must be 'rad' or 'deg'.")
        self.mode = m

    def wrap_trig(self, f: Callable[[float], float]) -> Callable[[float], float]:
        if self.mode == "rad":
            return f
        def g(x: float) -> float:
            return f(math.radians(x))
        return g

    def wrap_atrig(self, f: Callable[[float], float]) -> Callable[[float], float]:
        if self.mode == "rad":
            return f
        def g(x: float) -> float:
            return math.degrees(f(x))
        return g

# ---------------- MAIN PROGRAM ---------------- #

def build_env(trig: TrigMode, ans: float, mem: float):
    # names (constants + variables)
    names = {
        "pi": math.pi, "e": math.e, "tau": math.tau,
        "inf": math.inf, "nan": math.nan,
        "ans": ans, "mem": mem,
    }

    # functions
    funcs: Dict[str, Callable[..., float]] = {
        # basic math
        "abs": abs, "round": round,
        "floor": math.floor, "ceil": math.ceil,
        "sqrt": math.sqrt, "exp": math.exp,
        "log": math.log, "log10": math.log10,

        # trig (respect mode)
        "sin": trig.wrap_trig(math.sin),
        "cos": trig.wrap_trig(math.cos),
        "tan": trig.wrap_trig(math.tan),
        "asin": trig.wrap_atrig(math.asin),
        "acos": trig.wrap_atrig(math.acos),
        "atan": trig.wrap_atrig(math.atan),

        # factorial (integer-like only)
        "factorial": factorial_safe,
    }
    return names, funcs

def factorial_safe(x: float) -> float:
    # Allow non-negative integers or floats very close to ints
    n = int(round(x))
    if abs(x - n) > 1e-12 or n < 0:
        raise ValueError("factorial() only defined for non-negative integers.")
    return float(math.factorial(n))

def print_help():
    msg = """
Commands:
  help             Show this help
  history          Show recent results
  clear            Clear the screen (prints blank lines)
  mode deg|rad     Set trig mode (default: rad)
  precision N      Set decimal precision for printing (default: 12)
  m+ [x]           Add x (or ans if omitted) to memory
  m- [x]           Subtract x (or ans if omitted) from memory
  mr               Print memory value
  mc               Clear memory (set to 0)
  reset            Reset ans, mem, mode, precision, history
  quit / exit      Leave the calculator

Usage:
  - Enter math expressions directly:
      2+2, 2*(3+4)^2, 5!, sqrt(2), log(8,2), ln(5) -> use 'log(5)' for natural log
      sin(30) with mode deg OR sin(pi/6) with mode rad
  - Variables:
      ans (last answer), mem (memory register)
    """
    print(msg.strip())

def main():
    trig = TrigMode("rad")
    precision = 12
    ans = 0.0
    mem = 0.0
    history = []  # list[(expr, result)]

    def show_result(x: float):
        # Nicely format floats; show integers without decimal when exact
        if math.isfinite(x):
            if abs(x - int(x)) < 10**(-precision):
                print(int(round(x)))
            else:
                print(f"{x:.{precision}g}")
        else:
            print(x)

    print("Advanced Calculator. Type 'help' for commands. Ctrl+C to exit.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not line:
            continue

        # Commands
        lower = line.lower()
        if lower in ("quit", "exit"):
            print("Bye.")
            break
        if lower == "help":
            print_help()
            continue
        if lower == "history":
            if not history:
                print("(no history)")
            else:
                for i, (e, r) in enumerate(history[-20:], 1):  # last 20
                    print(f"{i:>2}: {e}  =  {r}")
            continue
        if lower.startswith("clear"):
            print("\n" * 60)
            continue
        if lower.startswith("mode"):
            parts = line.split()
            if len(parts) != 2 or parts[1].lower() not in ("deg", "rad"):
                print("Usage: mode deg|rad")
                continue
            trig.set_mode(parts[1].lower())
            print(f"Trig mode set to {trig.mode}.")
            continue
        if lower.startswith("precision"):
            parts = line.split()
            if len(parts) != 2 or not parts[1].isdigit():
                print("Usage: precision N")
                continue
            precision = max(1, min(50, int(parts[1])))
            print(f"Precision set to {precision}.")
            continue
        if lower == "mr":
            show_result(mem)
            continue
        if lower == "mc":
            mem = 0.0
            print("Memory cleared.")
            continue
        if lower.startswith("m+") or lower.startswith("m-"):
            op = line[:2].lower()  # 'm+' or 'm-'
            arg = line[2:].strip()
            if arg == "":
                delta = ans
            else:
                # Evaluate arg with current env
                names, funcs = build_env(trig, ans, mem)
                try:
                    delta = float(safe_eval(arg, names, funcs))
                except Exception as e:
                    print(f"Memory op error: {e}")
                    continue
            if op == "m+":
                mem += delta
            else:
                mem -= delta
            print(f"Memory = {mem}")
            continue
        if lower == "reset":
            trig = TrigMode("rad")
            precision = 12
            ans = 0.0
            mem = 0.0
            history.clear()
            print("State reset.")
            continue

        # Evaluate math expression
        names, funcs = build_env(trig, ans, mem)
        try:
            value = safe_eval(line, names, funcs)
            if not isinstance(value, (int, float)):
                raise ValueError("Expression did not produce a number.")
            ans = float(value)
            history.append((line, ans))
            show_result(ans)
        except ZeroDivisionError:
            print("Error: division by zero.")
        except OverflowError:
            print("Error: numeric overflow.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()


