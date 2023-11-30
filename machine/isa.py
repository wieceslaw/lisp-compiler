from enum import Enum


class Opcode(str, Enum):
    ADD = "add"
    SUB = "sub"
    MOD = "mod"
    AND = "and"
    OR = "or"
    NOT = "not"
    FLAGS = "flags"
    LD = "ld"
    ST = "st"
    PUT = "put"
    GET = "get"
    PUSH = "push"
    POP = "pop"
    JMP = "jmp"
    JZ = "jz"
    CALL = "call"
    RET = "ret"
    NOP = "nop"
    HALT = "halt"
