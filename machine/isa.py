from enum import Enum

from translator.lexer import TokenType, binary_operators, unary_operators


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
            TokenType.KEY_STORE: Opcode.ST,
            # TODO: Implement
            TokenType.EQUALS: Opcode.NOP,
            TokenType.GREATER: Opcode.NOP,
            TokenType.LESS: Opcode.NOP,
        }[token]

    @staticmethod
    def from_unary_operator(token: TokenType):
        assert token in unary_operators(), "Unknown unary operator: {}".format(token)
        return {
            TokenType.NOT: Opcode.NOT,
            TokenType.KEY_LOAD: Opcode.LD,
            TokenType.KEY_PUT: Opcode.PUT
        }[token]


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
