import re
from enum import Enum


class TokenType(str, Enum):
    OPEN_BRACKET = "T_OPEN_BRACKET"  # (
    CLOSE_BRACKET = "T_CLOSE_BRACKET"  # )
    STRING_LITERAL = "T_STRING_LITERAL"  # "\w*"
    CHARACTER_LITERAL = "T_CHARACTER_LITERAL"  # '.'
    NUMBER_LITERAL = "T_NUMBER_LITERAL"  # [0-9]+
    VARNAME = "T_VARNAME"  # \w+

    PLUS = "T_PLUS"  # +
    SUB = "T_SUB"  # -
    MUL = "T_MUL"  # *
    DIV = "T_DIV"  # /
    EQUALS = "T_EQUALS"  # =
    LESS = "T_LESS"  # <
    GREATER = "T_GREATER"  # >

    MOD = "T_MOD"  # mod
    AND = "T_AND"  # and
    OR = "T_OR"  # or
    NOT = "T_NOT"  # not

    KEY_DEFUN = "T_KEY_DEFUN"  # defun
    KEY_LOOP = "T_KEY_LOOP"  # loop
    KEY_SETQ = "T_KEY_SETQ"  # setq
    KEY_IF = "T_KEY_IF"  # if

    # KEY_ALLOC           = "T_KEY_ALLOC"         # alloc
    # KEY_PUT             = "T_KEY_PUT"           # put
    # KEY_GET             = "T_KEY_GET"           # get
    # KEY_LOAD            = "T_KEY_LOAD"          # load
    # KEY_STORE           = "T_KEY_STORE"         # store

    def __repr__(self):
        return self.value


tokens = [
    (r"\(", TokenType.OPEN_BRACKET),
    (r"\)", TokenType.CLOSE_BRACKET),
    (r"\+", TokenType.PLUS),
    (r"-", TokenType.SUB),
    (r"\*", TokenType.MUL),
    (r"/", TokenType.DIV),
    (r"=", TokenType.EQUALS),
    (r"<", TokenType.LESS),
    (r">", TokenType.GREATER),
    (r"mod", TokenType.MOD),
    (r"and", TokenType.AND),
    (r"or", TokenType.OR),
    (r"not", TokenType.NOT),
    (r"defun", TokenType.KEY_DEFUN),
    (r"loop", TokenType.KEY_LOOP),
    (r"setq", TokenType.KEY_SETQ),
    (r"if", TokenType.KEY_IF),
    (r"'.'", TokenType.CHARACTER_LITERAL),
    (r'"(.*)"', TokenType.STRING_LITERAL),
    (r"[0-9]+", TokenType.NUMBER_LITERAL),
    (r"[a-zA-Z]\w*", TokenType.VARNAME),
]
assert len(tokens) == len([i for i in TokenType])  # assert that all cases are matched
tokens = [(re.compile(pattern), ttype) for pattern, ttype in tokens]  # compile patterns


def operators():
    return {
        TokenType.MOD,
        TokenType.AND,
        TokenType.OR,
        TokenType.PLUS,
        TokenType.SUB,
        TokenType.MUL,
        TokenType.DIV,
        TokenType.EQUALS,
        TokenType.LESS,
        TokenType.GREATER,
    }


class Token:
    def __init__(self, token, line, offset):
        self.type = None
        self.value = None
        for pattern, token_type in tokens:
            match = pattern.match(token)
            if match:
                self.type = token_type
                if token_type == TokenType.STRING_LITERAL:
                    self.value = token[1:-1]
                elif token_type == TokenType.NUMBER_LITERAL:
                    assert token.isdigit()
                    self.value = int(token)
                elif token_type == TokenType.CHARACTER_LITERAL:
                    self.type = TokenType.NUMBER_LITERAL
                    self.value = ord(token[1:-1])
                else:
                    self.value = token
                break
        assert self.type is not None, "Unknown token"
        self.line = line
        self.offset = offset

    def __repr__(self):
        return f'Token[{self.type} "{self.value}" @ {self.line} {self.offset}]'


class Lexer:
    def __init__(self, text: str):
        self.ptr = 0
        self.text = text
        self.line = 0
        self.offset = 0

    def next(self) -> Token:
        if self._skip_empty():
            return None
        char = self.text[self.ptr]
        current_offset = self.offset
        if char in ["(", ")", "+", "-", "*", "/", "=", "<", ">"]:
            self.ptr += 1
            self.offset += 1
            return Token(char, self.line, current_offset)
        elif char == '"':
            return Token(self._read_string_literal(), self.line, current_offset)
        elif char == "'":
            return Token(self._read_character_literal(), self.line, current_offset)
        else:
            return Token(self._read_string(), self.line, current_offset)

    def _read_string(self) -> str:
        result = ""
        while not self._eof() and self._cur() not in ["(", ")", " ", "\n", "\t"]:
            result += self.text[self.ptr]
            self.ptr += 1
            self.offset += 1
        return result

    def _read_character_literal(self):
        result = ""
        assert self._cur() == "'"
        result += self._cur()
        self.ptr += 1
        result += self._cur()
        self.ptr += 1
        assert self._cur() == "'"
        result += self._cur()
        self.ptr += 1
        return result

    def _read_string_literal(self) -> str:
        result = '"'
        self.ptr += 1
        while not self._eof() and self._cur() != '"':
            result += self.text[self.ptr]
            self.ptr += 1
            self.offset += 1
        result += self._cur()
        self.ptr += 1
        return result

    def _skip_empty(self) -> bool:
        while not self._eof() and self._cur() in ["\n", " ", "\t", ";"]:
            if self._cur() == ";":
                while not self._eof():
                    if self._cur() == "\n":
                        self.ptr += 1
                        self.line += 1
                        self.offset = 0
                        break
                    self.ptr += 1
            elif self._cur() == "\n":
                self.line += 1
                self.offset = 0
                self.ptr += 1
            else:
                self.offset += 1
                self.ptr += 1
        return self._eof()

    def _eof(self) -> bool:
        return self.ptr == len(self.text)

    def _cur(self) -> str:
        assert not self._eof()
        return self.text[self.ptr]
