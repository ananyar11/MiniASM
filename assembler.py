"""MiniASM - Steps 6 and 7: Two-pass assembler core.

Pass 1: build the symbol table (label -> address).
Pass 2: generate 16-bit machine code, resolving labels via the symbol table.

Word format: | opcode (4 bits) | register (4 bits) | operand (8 bits) |
"""

import sys

from lexer import AsmError, tokenize_file

OPCODES = {
    "HALT": 0x0, "MOV": 0x1, "ADD": 0x2, "SUB": 0x3, "MUL": 0x4,
    "CMP": 0x5, "JMP": 0x6, "JZ": 0x7, "LOAD": 0x8, "STORE": 0x9,
}

# Operand shapes per mnemonic:
#   R = register, I = immediate/address (number), L = label
SHAPES = {
    "HALT": "",
    "MOV": "RI",
    "ADD": "RR", "SUB": "RR", "MUL": "RR", "CMP": "RR",
    "JMP": "L", "JZ": "L",
    "LOAD": "RI", "STORE": "RI",
}

REGISTERS = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


def pass1(lines):
    """Build the symbol table. Returns (symbols, instructions)."""
    symbols = {}
    instructions = []  # (address, lineno, mnemonic, operands, source)
    address = 0
    for lineno, tok, source in lines:
        if tok["label"] is not None:
            if tok["label"] in symbols:
                raise AsmError(lineno, f"duplicate label '{tok['label']}'")
            symbols[tok["label"]] = address
        if tok["mnemonic"] is not None:
            instructions.append((address, lineno, tok["mnemonic"], tok["operands"], source))
            address += 1
    return symbols, instructions


def parse_number(text, lineno):
    try:
        value = int(text, 0)  # handles decimal and 0x.. hex
    except ValueError:
        raise AsmError(lineno, f"invalid number '{text}'")
    if not 0 <= value <= 255:
        raise AsmError(lineno, f"value {value} out of range (0-255)")
    return value


def parse_register(text, lineno):
    reg = text.upper()
    if reg not in REGISTERS:
        raise AsmError(lineno, f"invalid register '{text}' (use R0-R3)")
    return REGISTERS[reg]


def pass2(symbols, instructions):
    """Generate machine code. Returns list of (address, word, source)."""
    output = []
    for address, lineno, mnemonic, operands, source in instructions:
        shape = SHAPES[mnemonic]
        if len(operands) != len(shape):
            raise AsmError(
                lineno, f"{mnemonic} expects {len(shape)} operand(s), got {len(operands)}"
            )

        reg_field = 0
        operand_field = 0

        if shape == "RI":
            reg_field = parse_register(operands[0], lineno)
            operand_field = parse_number(operands[1], lineno)
        elif shape == "RR":
            reg_field = parse_register(operands[0], lineno)
            operand_field = parse_register(operands[1], lineno)
        elif shape == "L":
            label = operands[0]
            if label not in symbols:
                raise AsmError(lineno, f"undefined label '{label}'")
            operand_field = symbols[label]

        word = (OPCODES[mnemonic] << 12) | (reg_field << 8) | operand_field
        output.append((address, word, source))
    return output


def assemble(path):
    lines = tokenize_file(path)
    symbols, instructions = pass1(lines)
    return symbols, pass2(symbols, instructions)


def write_hex(path, code):
    """One 4-digit hex word per line."""
    with open(path, "w") as f:
        for _, word, _ in code:
            f.write(f"{word:04X}\n")


def write_listing(path, symbols, code):
    """Readable listing: address | machine code (hex + binary) | source."""
    with open(path, "w") as f:
        f.write("ADDR  HEX   BINARY              SOURCE\n")
        f.write("----  ----  ------------------  ------------------------\n")
        for address, word, source in code:
            binary = f"{word:016b}"
            grouped = f"{binary[:4]} {binary[4:8]} {binary[8:]}"
            f.write(f"{address:04d}  {word:04X}  {grouped}  {source.strip()}\n")
        f.write("\nSYMBOL TABLE\n")
        f.write("------------\n")
        for label, address in symbols.items():
            f.write(f"{label:<12} {address:04d}\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <file.asm>")
        sys.exit(1)

    source_path = sys.argv[1]
    base = source_path.rsplit(".", 1)[0]

    try:
        symbols, code = assemble(source_path)
    except FileNotFoundError:
        print(f"Error: file '{source_path}' not found")
        sys.exit(1)
    except AsmError as e:
        print(f"Error: {e}")
        sys.exit(1)

    write_hex(base + ".hex", code)
    write_listing(base + ".lst", symbols, code)

    print(f"Assembled {len(code)} instruction(s) from {source_path}")
    print(f"  -> {base}.hex")
    print(f"  -> {base}.lst")


if __name__ == "__main__":
    main()
