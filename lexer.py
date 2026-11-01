"""MiniASM - Step 5: Lexer.

Splits one line of assembly into: label, mnemonic, operands.
Comments (after ';') and extra whitespace are removed.
"""

MNEMONICS = {"HALT", "MOV", "ADD", "SUB", "MUL", "CMP", "JMP", "JZ", "LOAD", "STORE"}


class AsmError(Exception):
    """Raised for any assembly error, with the line number."""

    def __init__(self, lineno, message):
        super().__init__(f"Line {lineno}: {message}")


def tokenize_line(line, lineno):
    """Return a dict {label, mnemonic, operands} or None for blank/comment lines."""
    # 1. Remove comment
    line = line.split(";", 1)[0].strip()
    if not line:
        return None

    label = None

    # 2. Extract label (anything before ':')
    if ":" in line:
        label, line = line.split(":", 1)
        label = label.strip()
        line = line.strip()
        if not label or not (label[0].isalpha() or label[0] == "_") \
                or not all(c.isalnum() or c == "_" for c in label):
            raise AsmError(lineno, f"invalid label '{label}'")
        if label.upper() in MNEMONICS:
            raise AsmError(lineno, f"label '{label}' clashes with a mnemonic")

    # 3. Label-only line
    if not line:
        return {"label": label, "mnemonic": None, "operands": []}

    # 4. Split mnemonic and operands
    parts = line.split(None, 1)
    mnemonic = parts[0].upper()
    if mnemonic not in MNEMONICS:
        raise AsmError(lineno, f"unknown mnemonic '{parts[0]}'")

    operands = []
    if len(parts) > 1:
        operands = [op.strip() for op in parts[1].split(",")]
        if any(op == "" for op in operands):
            raise AsmError(lineno, "empty operand (check your commas)")

    return {"label": label, "mnemonic": mnemonic, "operands": operands}


def tokenize_file(path):
    """Tokenize a whole file. Returns a list of (lineno, tokens, original_line)."""
    result = []
    with open(path) as f:
        for lineno, raw in enumerate(f, start=1):
            tokens = tokenize_line(raw, lineno)
            if tokens is not None:
                result.append((lineno, tokens, raw.rstrip("\n")))
    return result


if __name__ == "__main__":
    import sys

    for lineno, tok, _ in tokenize_file(sys.argv[1]):
        print(lineno, tok)
