"""MiniASM - Simulator.

Runs the machine code produced by the assembler (.hex file) and shows what happens.

Usage:  python simulator.py prog3.hex          (shows every step + final state)
        python simulator.py prog3.hex --quiet  (final state only)

Machine: 4 registers (R0-R3), 256 memory cells, program counter (PC), zero flag.
Word format: | opcode (4 bits) | register (4 bits) | operand (8 bits) |
"""

import sys

MAX_STEPS = 1000  # stops runaway programs (e.g. an infinite loop)

NAMES = {
    0x0: "HALT", 0x1: "MOV", 0x2: "ADD", 0x3: "SUB", 0x4: "MUL",
    0x5: "CMP", 0x6: "JMP", 0x7: "JZ", 0x8: "LOAD", 0x9: "STORE",
}


class SimError(Exception):
    pass


def load_program(path):
    program = []
    with open(path) as f:
        for lineno, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                word = int(text, 16)
            except ValueError:
                raise SimError(f"{path}, line {lineno}: '{text}' is not a hex word")
            if not 0 <= word <= 0xFFFF:
                raise SimError(f"{path}, line {lineno}: '{text}' is not a 16-bit word")
            program.append(word)
    return program


def describe(opcode, reg, operand):
    name = NAMES[opcode]
    if name == "HALT":
        return "HALT"
    if name in ("MOV", "LOAD", "STORE"):
        return f"{name} R{reg}, {operand}"
    if name in ("ADD", "SUB", "MUL", "CMP"):
        return f"{name} R{reg}, R{operand}"
    return f"{name} {operand}"


def run(program, trace=True):
    regs = [0, 0, 0, 0]
    memory = [0] * 256
    pc = 0
    zero = False
    steps = 0

    if trace:
        print(f"{'STEP':<5} {'PC':<3} {'WORD':<5} {'INSTRUCTION':<14} "
              f"{'R0':>4} {'R1':>4} {'R2':>4} {'R3':>4}  ZERO")
        print("-" * 58)

    while True:
        if pc >= len(program):
            raise SimError(f"PC={pc} ran past the end of the program (missing HALT?)")
        if steps >= MAX_STEPS:
            raise SimError(f"stopped after {MAX_STEPS} steps (possible infinite loop)")

        word = program[pc]
        opcode = (word >> 12) & 0xF
        reg = (word >> 8) & 0xF
        operand = word & 0xFF

        if opcode not in NAMES:
            raise SimError(f"PC={pc}: unknown opcode {opcode:X} in word {word:04X}")
        if opcode in (0x1, 0x2, 0x3, 0x4, 0x5, 0x8, 0x9) and reg > 3:
            raise SimError(f"PC={pc}: invalid register R{reg}")
        if opcode in (0x2, 0x3, 0x4, 0x5) and operand > 3:
            raise SimError(f"PC={pc}: invalid register R{operand}")

        text = describe(opcode, reg, operand)
        steps += 1
        next_pc = pc + 1
        halted = False

        if opcode == 0x0:      # HALT
            halted = True
        elif opcode == 0x1:    # MOV Rd, imm
            regs[reg] = operand
        elif opcode == 0x2:    # ADD
            regs[reg] = (regs[reg] + regs[operand]) & 0xFFFF
        elif opcode == 0x3:    # SUB
            regs[reg] = (regs[reg] - regs[operand]) & 0xFFFF
        elif opcode == 0x4:    # MUL
            regs[reg] = (regs[reg] * regs[operand]) & 0xFFFF
        elif opcode == 0x5:    # CMP
            zero = regs[reg] == regs[operand]
        elif opcode == 0x6:    # JMP
            next_pc = operand
        elif opcode == 0x7:    # JZ
            if zero:
                next_pc = operand
        elif opcode == 0x8:    # LOAD
            regs[reg] = memory[operand]
        elif opcode == 0x9:    # STORE
            memory[operand] = regs[reg]

        if trace:
            print(f"{steps:<5} {pc:<3} {word:04X}  {text:<14} "
                  f"{regs[0]:>4} {regs[1]:>4} {regs[2]:>4} {regs[3]:>4}  {int(zero)}")

        if halted:
            break
        pc = next_pc

    return regs, memory, steps


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    trace = "--quiet" not in sys.argv
    if len(args) != 1:
        print("Usage: python simulator.py <file.hex> [--quiet]")
        sys.exit(1)

    try:
        program = load_program(args[0])
        regs, memory, steps = run(program, trace)
    except FileNotFoundError:
        print(f"Error: file '{args[0]}' not found")
        sys.exit(1)
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
