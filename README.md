# Advanced CLI Calculator

An advanced command-line calculator built in Python.  
It safely evaluates math expressions using Python's AST parser and supports variables, history, memory, and scientific functions.

---

## ✨ Features
- **Operators:** `+`, `-`, `*`, `/`, `//`, `%`, `**` (or `^`)
- **Expressions with parentheses:**  
  Example: `2*(3+4)^2 / 7`
- **Functions:**  
  - Trigonometry: `sin`, `cos`, `tan`, `asin`, `acos`, `atan`  
  - Exponentials & logs: `exp`, `log` (base e), `log10`, `ln` (alias for `log`)  
  - Other math: `sqrt`, `floor`, `ceil`, `round`, `abs`  
  - Factorial: `n!` or `factorial(n)`
- **Constants:** `pi`, `e`, `tau`, `inf`, `nan`
- **Variables:**  
  - `ans` → last computed answer  
  - `mem` → memory register
- **Modes:** Degrees or radians for trig functions
- **Precision:** Adjustable decimal output
- **History:** Stores your recent results
- **Safe:** Uses AST parsing, no `eval`/`exec`

---

## 🛠 Installation
1. Make sure you have **Python 3.8+** installed.
2. Clone or download this repo.
3. Run the calculator:
   ```bash
   python calculator.py
Advanced Calculator. Type 'help' for commands. Ctrl+C to exit.
