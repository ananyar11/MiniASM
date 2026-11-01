# MiniASM: A Two-Pass Assembler for a Custom Instruction Set

A mini project for **Compiler Construction Lab (23CE701P)**, Department of Computer Engineering, St. Vincent Pallotti College of Engineering & Technology, Nagpur (Session 2026-27).

MiniASM translates assembly programs written for a small custom instruction set into 16-bit machine code. It is implemented twice, in **Python** and in **Flex with C**, and both versions give identical output. A simulator runs the generated machine code so the result can be checked.

## How it works

The assembler reads the program **twice**:

1. **Pass 1** assigns an address to every instruction and stores each label with its address in a symbol table.
2. **Pass 2** generates the machine code and looks up label addresses in the symbol table. This is why a jump to a label defined later in the program (a forward reference) works.

Compiler phases covered: lexical analysis and code generation.

## Instruction set

The machine has four registers (R0 to R3), 256 memory cells, a program counter and a zero flag.

| Mnemonic | Format | Meaning | Opcode |
|---|---|---|---|
| HALT | `HALT` | Stop execution | 0x0 |
| MOV | `MOV Rd, imm` | Rd = immediate value | 0x1 |
| ADD | `ADD Rd, Rs` | Rd = Rd + Rs | 0x2 |
| SUB | `SUB Rd, Rs` | Rd = Rd - Rs | 0x3 |
| MUL | `MUL Rd, Rs` | Rd = Rd * Rs | 0x4 |
| CMP | `CMP Rd, Rs` | Set the zero flag if Rd equals Rs | 0x5 |
| JMP | `JMP label` | Jump to the label | 0x6 |
| JZ | `JZ label` | Jump to the label if the zero flag is set | 0x7 |
| LOAD | `LOAD Rd, addr` | Rd = memory[addr] | 0x8 |
| STORE | `STORE Rd, addr` | memory[addr] = Rd | 0x9 |

**Machine code format** (one 16-bit word):

```
| opcode (4 bits) | register (4 bits) | operand (8 bits) |
```

Example: `MOV R1, 5` becomes `1105`.

**Source syntax:** one instruction per line, labels end with `:`, comments start with `;`, operands are separated by commas, numbers can be decimal or hex (`0x0A`).

## Project files

| File | Purpose |
|---|---|
| `lexer.py` | Splits each line into label, mnemonic and operands |
| `assembler.py` | Python two-pass assembler (writes `.hex` and `.lst`) |
| `simulator.py` | Runs a `.hex` file and shows registers and memory |
| `run.py` | Assembles and simulates in one step |
| `miniasm.l` | Flex version of the assembler |
| `prog1.asm`, `prog2.asm`, `prog3.asm` | Sample programs (addition, forward jump, countdown loop) |
| `err1.asm` to `err5.asm` | Programs with deliberate mistakes to test error messages |

## Usage

### Python version

```
python assembler.py prog3.asm      # writes prog3.hex and prog3.lst
python simulator.py prog3.hex      # runs the machine code step by step
python run.py prog3.asm            # assemble and run in one step
python run.py prog3.asm --quiet    # show only the final result
```

### Flex version (Windows)

Requires Flex (`win_flex`) and `gcc` (MinGW).

```
win_flex miniasm.l
gcc lex.yy.c -o miniasm
miniasm prog3.asm
```

On Linux or macOS use `flex miniasm.l` and `gcc lex.yy.c -o miniasm`.

## Example

`prog3.asm` counts a register down from 3 to 0:

```
       MOV R0, 3
       MOV R1, 1
       MOV R2, 0
LOOP:  SUB R0, R1
       CMP R0, R2
       JZ DONE
       JMP LOOP
DONE:  HALT
```

Machine code: `1003 1101 1200 3001 5002 7007 6003 0000`

Running `python run.py prog3.asm` shows R0 going 3, 2, 1, 0 and the program stopping after 15 steps.

## Error handling

Errors are reported with the line number and no output files are written, for example:

```
Error: Line 1: undefined label 'NOWHERE'
Error: Line 1: invalid register 'R9' (use R0-R3)
Error: Line 1: unknown mnemonic 'FOO'
Error: Line 1: value 300 out of range (0-255)
Error: Line 1: ADD expects 2 operand(s), got 1
```

## Author

Ananya N. Rajurkar (UID 23001123, Batch A2)
Guided by Ms. Akansha Bodade and Dr. Roshan R. Kotkondawar
