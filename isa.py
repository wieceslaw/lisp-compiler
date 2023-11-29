from enum import Enum

from lexer import binary_operators, TokenType, unary_operators, nullary_operators


class Opcode(str, Enum):
    PUT = "put"  # (0: value)
    GET = "get"
    STORE = "store"  # (0: addr, 1: value)
    LOAD = "load"  # (0: addr)
    PUSH = "push"  # <value>
    POP = "pop"
    JZ = "jz"
    JMP = "jmp"
    ADD = "add"  # (0: value, 1: value)
    SUB = "sub"  # (0: value, 1: value)
    MOD = "mod"  # (0: value, 1: value)
    AND = "and"  # (0: value, 1: value)
    OR = "or"  # (0: value, 1: value)
    NOT = "not"  # (0: value)
    CALL = "call"
    RET = "ret"
    NOP = "nop"
    SIGN = "sign"
    HALT = "halt"

    # MACRO INSTRUCTIONS
    # takes two values on the stack and pushes flag mask of their subtraction (- 1 2) -> 0x[POSITIVE, NEGATIVE, ZERO]
    LE = "le"  # (0: value, 1: value)
    EQ = "eq"  # (0: value, 1: value)
    GR = "gr"  # (0: value, 1: value)

    def __repr__(self):
        return self.name

    @staticmethod
    def from_binary_operator(token: TokenType):
        assert token in binary_operators(), "Unknown binary operator: {}".format(token)
        return {
            TokenType.MOD: Opcode.MOD,
            TokenType.AND: Opcode.AND,
            TokenType.OR: Opcode.OR,
            TokenType.PLUS: Opcode.ADD,
            TokenType.SUB: Opcode.SUB,
            TokenType.EQUALS: Opcode.EQ,
            TokenType.GREATER: Opcode.GR,
            TokenType.LESS: Opcode.LE,
            TokenType.KEY_STORE: Opcode.STORE
        }[token]

    @staticmethod
    def from_unary_operator(token: TokenType):
        assert token in unary_operators(), "Unknown unary operator: {}".format(token)
        return {
            TokenType.NOT: Opcode.NOT,
            TokenType.KEY_LOAD: Opcode.LOAD,
            TokenType.KEY_PUT: Opcode.PUT
        }[token]

    @staticmethod
    def from_nullary_operator(token: TokenType):
        assert token in nullary_operators(), "Unknown nullary operator: {}".format(token)
        return {
            TokenType.KEY_GET: Opcode.GET
        }[token]


class Addressing(str, Enum):
    RELATIVE_INDIRECT = "relative-indirect"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"
    IMMEDIATE = "immediate"

    def __repr__(self):
        return self.name


class Register(str, Enum):
    STACK_POINTER = "sp"
    FRAME_POINTER = "fp"

    def __repr__(self):
        return self.name
