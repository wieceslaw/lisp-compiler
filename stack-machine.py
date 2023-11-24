from enum import Enum

class OpCode(str, Enum):
    PUT     = "put"     # (0: value)
    GET     = "get"
    STORE   = "store"   # (0: addr, 1: value)
    LOAD    = "load"    # (0: addr)
    LSTORE  = "lstore"  # (0: i, 1: value)
    LLOAD   = "lload"   # (0: i)
    PUSH    = "push"    # <op>
    POP     = "pop"
    SWAP    = "swap"
    HALT    = "halt"
    JZ      = "jz"
    JNZ     = "jnz"
    JL      = "jl"
    JG      = "jg"
    JMP     = "jmp"
    ADD     = "add"     # (0: value, 1: value)
    SUB     = "sub"     # (0: value, 1: value)
    MUL     = "mul"     # (0: value, 1: value)
    MOD     = "mod"     # (0: value, 1: value)
    AND     = "and"     # (0: value, 1: value)
    OR      = "or"      # (0: value, 1: value)
    NOT     = "not"     # (0: value)

class StackMachine:
    def __init__(self):
        self.state = []

    def execute(self, program: list):
        pass
