from enum import Enum


class Opcode(str, Enum):
    ADD = "add"
    SUB = "sub"
    MOD = "mod"
    AND = "and"
    OR = "or"
    NOT = "not"
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
    ISPOS = "ispos"
    ISNEG = "isneg"
    ISZERO = "iszero"
    NOP = "nop"
    HALT = "halt"

    def __repr__(self):
        return self.name


class Addressing(str, Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    RELATIVE_INDIRECT = "relative-indirect"

    def __repr__(self):
        return self.name


class Register(str, Enum):
    STACK_POINTER = "sp"
    FRAME_POINTER = "fp"

    def __repr__(self):
        return self.name
