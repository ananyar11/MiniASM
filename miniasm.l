/* MiniASM - Flex version: Two-Pass Assembler for a Custom Instruction Set
 *
 * Build:   flex miniasm.l
 *          gcc lex.yy.c -o miniasm
 * Run:     ./miniasm prog3.asm      (writes prog3.hex and prog3.lst)
 *
 * Word format: | opcode (4 bits) | register (4 bits) | operand (8 bits) |
 *
 * Flex does the lexical analysis (tokens). The C code below does:
 *   - line collection while scanning
 *   - Pass 1: build the symbol table (label -> address)
 *   - Pass 2: generate machine code, resolving labels
 */

%option noyywrap
%option case-insensitive

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>
#include <strings.h>

#define MAX_LINES   1024
#define MAX_LABELS  256
#define NAME_LEN    64
#define SRC_LEN     256

/* Opcode = index in this table */
static const char *MNEMONICS[10] = {
    "HALT", "MOV", "ADD", "SUB", "MUL", "CMP", "JMP", "JZ", "LOAD", "STORE"
};
/* Operand shapes: R = register, I = number, L = label */
static const char *SHAPES[10] = {
    "", "RI", "RR", "RR", "RR", "RR", "L", "L", "RI", "RI"
};

typedef struct {
    int  lineno;
    int  has_label;
    char label[NAME_LEN];
    int  has_instr;
    int  opcode;
    int  nops;                 /* operands seen (may exceed stored 2) */
    char ops[2][NAME_LEN];
    int  addr;                 /* filled in by pass 1 */
} Line;

typedef struct { char name[NAME_LEN]; int addr; } Symbol;

static Line   lines[MAX_LINES];
static int    nlines = 0;
static Line   cur;             /* line being built */
static int    last_comma = 0;
static int    lineno = 1;

static Symbol symbols[MAX_LABELS];
static int    nsymbols = 0;

static int    words[MAX_LINES];       /* machine code, one per instruction */
static int    word_addr[MAX_LINES];
static int    word_line[MAX_LINES];
static int    nwords = 0;

static char   src[MAX_LINES + 2][SRC_LEN];   /* original source lines */

static void die(int line, const char *fmt, ...)
{
    va_list ap;
    printf("Error: Line %d: ", line);
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    exit(1);
}

static int mnemonic_index(const char *text)
{
    int i;
    for (i = 0; i < 10; i++)
        if (strcasecmp(text, MNEMONICS[i]) == 0) return i;
    return -1;
}

static void reset_cur(void)
{
    memset(&cur, 0, sizeof(cur));
    last_comma = 0;
}

/* ---------- actions called by the Flex rules ---------- */

static void on_label(const char *text)
{
    char name[NAME_LEN];
    size_t n = 0;
    while (text[n] != ':' && !isspace((unsigned char)text[n]) && n < NAME_LEN - 1) {
        name[n] = text[n];
        n++;
    }
    name[n] = '\0';

    if (cur.has_label) die(lineno, "only one label allowed per line");
    if (cur.has_instr) die(lineno, "label '%s' must come before the instruction", name);
    if (mnemonic_index(name) >= 0)
        die(lineno, "label '%s' clashes with a mnemonic", name);

    cur.has_label = 1;
    strcpy(cur.label, name);
}

static void on_mnemonic(const char *text)
{
    if (cur.has_instr) die(lineno, "unexpected '%s' (mnemonic used as operand)", text);
    cur.has_instr = 1;
    cur.opcode = mnemonic_index(text);
    cur.nops = 0;
    last_comma = 0;
}

static void on_operand(const char *text)
{
    if (!cur.has_instr) die(lineno, "unknown mnemonic '%s'", text);
    if (cur.nops > 0 && !last_comma) die(lineno, "missing comma between operands");
    if (cur.nops < 2) {
        strncpy(cur.ops[cur.nops], text, NAME_LEN - 1);
        cur.ops[cur.nops][NAME_LEN - 1] = '\0';
    }
    cur.nops++;
    last_comma = 0;
}

static void on_comma(void)
{
    if (!cur.has_instr) die(lineno, "unexpected ','");
    if (cur.nops == 0 || last_comma) die(lineno, "empty operand (check your commas)");
    last_comma = 1;
}

static void end_line(void)
{
    if (last_comma) die(lineno, "empty operand (check your commas)");
    if (cur.has_label || cur.has_instr) {
        if (nlines >= MAX_LINES) die(lineno, "program too large");
        cur.lineno = lineno;
        lines[nlines++] = cur;
    }
    reset_cur();
}

/* ---------- Pass 1: symbol table ---------- */

static void pass1(void)
{
    int i, j, address = 0;
    for (i = 0; i < nlines; i++) {
        if (lines[i].has_label) {
            for (j = 0; j < nsymbols; j++)
                if (strcmp(symbols[j].name, lines[i].label) == 0)
                    die(lines[i].lineno, "duplicate label '%s'", lines[i].label);
            if (nsymbols >= MAX_LABELS) die(lines[i].lineno, "too many labels");
            strcpy(symbols[nsymbols].name, lines[i].label);
            symbols[nsymbols].addr = address;
            nsymbols++;
        }
        if (lines[i].has_instr) {
            lines[i].addr = address;
            address++;
        }
    }
}

/* ---------- Pass 2: code generation ---------- */

static int parse_register(const char *text, int lineno_)
{
    if (strlen(text) == 2 && toupper((unsigned char)text[0]) == 'R'
        && text[1] >= '0' && text[1] <= '3')
        return text[1] - '0';
    die(lineno_, "invalid register '%s' (use R0-R3)", text);
    return 0;
}

static int parse_number(const char *text, int lineno_)
{
    char *end;
    int base = (text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) ? 16 : 10;
    long v = strtol(text, &end, base);
    if (end == text || *end != '\0') die(lineno_, "invalid number '%s'", text);
    if (v < 0 || v > 255) die(lineno_, "value %ld out of range (0-255)", v);
    return (int)v;
}

static int lookup_label(const char *name, int lineno_)
{
    int i;
    for (i = 0; i < nsymbols; i++)
        if (strcmp(symbols[i].name, name) == 0) return symbols[i].addr;
    die(lineno_, "undefined label '%s'", name);
    return 0;
}

static void pass2(void)
{
    int i;
    for (i = 0; i < nlines; i++) {
        Line *l = &lines[i];
        const char *shape;
        int reg_field = 0, operand_field = 0, word;

        if (!l->has_instr) continue;
        shape = SHAPES[l->opcode];

        if (l->nops != (int)strlen(shape))
            die(l->lineno, "%s expects %d operand(s), got %d",
                MNEMONICS[l->opcode], (int)strlen(shape), l->nops);

        if (strcmp(shape, "RI") == 0) {
            reg_field = parse_register(l->ops[0], l->lineno);
            operand_field = parse_number(l->ops[1], l->lineno);
        } else if (strcmp(shape, "RR") == 0) {
            reg_field = parse_register(l->ops[0], l->lineno);
            operand_field = parse_register(l->ops[1], l->lineno);
        } else if (strcmp(shape, "L") == 0) {
            operand_field = lookup_label(l->ops[0], l->lineno);
        }

        word = (l->opcode << 12) | (reg_field << 8) | operand_field;
        words[nwords] = word;
        word_addr[nwords] = l->addr;
        word_line[nwords] = l->lineno;
        nwords++;
    }
}

/* ---------- Output ---------- */

static void trim(char *s)
{
    size_t n;
    char *p = s;
    while (*p && isspace((unsigned char)*p)) p++;
    memmove(s, p, strlen(p) + 1);
    n = strlen(s);
    while (n > 0 && isspace((unsigned char)s[n - 1])) s[--n] = '\0';
}

static void write_hex(const char *path)
{
    int i;
    FILE *f = fopen(path, "w");
    if (!f) { printf("Error: cannot write '%s'\n", path); exit(1); }
    for (i = 0; i < nwords; i++) fprintf(f, "%04X\n", words[i]);
    fclose(f);
}

static void write_listing(const char *path)
{
    int i, b;
    FILE *f = fopen(path, "w");
    if (!f) { printf("Error: cannot write '%s'\n", path); exit(1); }
    fprintf(f, "ADDR  HEX   BINARY              SOURCE\n");
    fprintf(f, "----  ----  ------------------  ------------------------\n");
    for (i = 0; i < nwords; i++) {
        char text[SRC_LEN];
        strcpy(text, src[word_line[i]]);
        trim(text);
        fprintf(f, "%04d  %04X  ", word_addr[i], words[i]);
        for (b = 15; b >= 0; b--) {
            fputc((words[i] >> b) & 1 ? '1' : '0', f);
            if (b == 12 || b == 8) fputc(' ', f);
        }
        fprintf(f, "  %s\n", text);
    }
    fprintf(f, "\nSYMBOL TABLE\n------------\n");
    for (i = 0; i < nsymbols; i++)
        fprintf(f, "%-12s %04d\n", symbols[i].name, symbols[i].addr);
    fclose(f);
}
%}

%%

[ \t\r]+                                      { /* skip whitespace */ }
";"[^\n]*                                     { /* skip comment */ }
\n                                            { end_line(); lineno++; }
","                                           { on_comma(); }
HALT|MOV|ADD|SUB|MUL|CMP|JMP|JZ|LOAD|STORE   { on_mnemonic(yytext); }
[A-Za-z_][A-Za-z0-9_]*[ \t]*":"               { on_label(yytext); }
0[xX][0-9a-fA-F]+|[0-9]+|[A-Za-z_][A-Za-z0-9_]*   { on_operand(yytext); }
.                                             { die(lineno, "unexpected character '%s'", yytext); }
<<EOF>>                                       { end_line(); return 0; }

%%

int main(int argc, char *argv[])
{
    char base[512], hexpath[528], lstpath[528], *dot;
    FILE *f;
    int n = 1;

    if (argc != 2) {
        printf("Usage: %s <file.asm>\n", argv[0]);
        return 1;
    }

    f = fopen(argv[1], "r");
    if (!f) {
        printf("Error: file '%s' not found\n", argv[1]);
        return 1;
    }

    /* keep the original source lines for the listing */
    while (n <= MAX_LINES && fgets(src[n], SRC_LEN, f)) n++;
    rewind(f);

    reset_cur();
    yyin = f;
    yylex();          /* scan the file and collect lines */
    fclose(f);

    pass1();          /* Pass 1: symbol table */
    pass2();          /* Pass 2: machine code */

    strncpy(base, argv[1], sizeof(base) - 1);
    base[sizeof(base) - 1] = '\0';
    dot = strrchr(base, '.');
    if (dot) *dot = '\0';
    sprintf(hexpath, "%s.hex", base);
    sprintf(lstpath, "%s.lst", base);

    write_hex(hexpath);
    write_listing(lstpath);

    printf("Assembled %d instruction(s) from %s\n", nwords, argv[1]);
    printf("  -> %s\n  -> %s\n", hexpath, lstpath);
    return 0;
}
