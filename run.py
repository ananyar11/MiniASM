"""MiniASM - Run: assemble a .asm file and simulate it in one step.

Usage:  python run.py prog3.asm            (assemble, then show every step)
        python run.py prog3.asm --quiet    (assemble, then final state only)

Also writes the .hex and .lst files, exactly like assembler.py does.
"""

import sys

from lexer import AsmError
from assembler import assemble, write_hex, write_listing
from simulator import run, SimError


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    trace = "--quiet" not in sys.argv
    if len(args) != 1:
        print("Usage: python run.py <file.asm> [--quiet]")
        sys.exit(1)

    path = args[0]
    base = path.rsplit(".", 1)[0]

    # Stage 1: assemble
    try:
        symbols, code = assemble(path)
    except FileNotFoundError:
        print(f"Error: file '{path}' not found")
        sys.exit(1)
    except AsmError as e:
        print(f"Assembly failed: {e}")
        sys.exit(1)

    write_hex(base + ".hex", code)
    write_listing(base + ".lst", symbols, code)
    print(f"[1/2] Assembled {len(code)} instruction(s) -> {base}.hex, {base}.lst")
    print("      Symbol table:", symbols if symbols else "(no labels)")
    print()

    # Stage 2: simulate
    print("[2/2] Running the program:")
    try:
        regs, memory, steps = run([word for _, word, _ in code], trace)
    except SimError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print()
    print(f"Program finished in {steps} step(s).")
    print("Registers:", "  ".join(f"R{i}={v}" for i, v in enumerate(regs)))
    used = {a: v for a, v in enumerate(memory) if v != 0}
    print("Memory   :", "  ".join(f"[{a}]={v}" for a, v in used.items()) or "(all zero)")


if __name__ == "__main__":
    main()
