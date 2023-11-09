import re
from enum import Enum

class TokenType(str, Enum):
    OPEN_BRACKET        = "T_OPEN_BRACKET"      # (
    CLOSE_BRACKET       = "T_CLOSE_BRACKET"     # )
    STRING_LITERAL      = "T_STRING_LITERAL"    # "\w*"
    CHARACTER_LITERAL   = "T_CHARACTER_LITERAL" # '.'
    NUMBER_LITERAL      = "T_NUMBER_LITERAL"    # [0-9]+
    VARNAME             = "T_VARNAME"           # \w+

    PLUS                = "T_PLUS"              # +
    SUB                 = "T_SUB"               # -
    MUL                 = "T_MUL"               # *
    DIV                 = "T_DIV"               # /
    EQUALS              = "T_EQUALS"            # =
    LESS                = "T_LESS"              # <
    GREATER             = "T_GREATER"           # >

    MOD                 = "T_MOD"               # mod
    AND                 = "T_AND"               # and
    OR                  = "T_OR"                # or
    NOT                 = "T_NOT"               # not

    KEY_DEFUN           = "T_KEY_DEFUN"         # defun
    KEY_LOOP            = "T_KEY_LOOP"          # loop
    KEY_SETQ            = "T_KEY_SETQ"          # setq
    KEY_IF              = "T_KEY_IF"            # if

    KEY_ALLOC           = "T_KEY_ALLOC"         # alloc
    KEY_PUT             = "T_KEY_PUT"           # put
    KEY_GET             = "T_KEY_GET"           # get
    KEY_LOAD            = "T_KEY_LOAD"          # load
    KEY_STORE           = "T_KEY_STORE"         # store


    def __repr__(self):
        return self.value


tokens = [
    (r"\(",             TokenType.OPEN_BRACKET),
    (r"\)",             TokenType.CLOSE_BRACKET),
    (r"\+",             TokenType.PLUS),
    (r"-",              TokenType.SUB),
    (r"\*",             TokenType.MUL),
    (r"/",              TokenType.DIV),
    (r"=",              TokenType.EQUALS),
    (r"<",              TokenType.LESS),
    (r">",              TokenType.GREATER),
    (r"mod",            TokenType.MOD),
    (r"and",            TokenType.AND),
    (r"or",             TokenType.OR),
    (r"not",            TokenType.NOT),
    (r"defun",          TokenType.KEY_DEFUN),
    (r"loop",           TokenType.KEY_LOOP),
    (r"setq",           TokenType.KEY_SETQ),
    (r"if",             TokenType.KEY_IF),
    (r"'.'",            TokenType.CHARACTER_LITERAL),
    (r'"(.*)"',         TokenType.STRING_LITERAL),
    (r"[0-9]+",         TokenType.NUMBER_LITERAL),
    (r"[a-zA-Z]\w*",    TokenType.VARNAME),
]
assert len(tokens) == len([i for i in TokenType])  # assert that all cases are matched
tokens = [(re.compile(pattern), ttype) for pattern, ttype in tokens]  # compile patterns


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
        assert self._cur() == "'"
        self.ptr += 1
        char = self._cur()
        self.ptr += 1
        assert self._cur() == "'"
        self.ptr += 1
        return char

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

class Expression:
    def __repr__(self):
        return "EMPTY"

class FunctionCallExpression(Expression):
    def __init__(self, name: str, arguments: list[Expression]):
        self.name = name
        self.arguments = arguments

    def __repr__(self) -> str:
        return 'FUNCTION CALL [NAME: "{}", ARGUMENTS: {}]'.format(self.name, self.arguments)

class NumberLiteralExpression(Expression):
    def __init__(self, value: int):
        self.value = value

    def __repr__(self) -> str:
        return 'NUMBER LITERAL [VALUE: "{}"]'.format(self.value)

class StringLiteralExpression(Expression):
    def __init__(self, value: str):
        self.value = value

    def __repr__(self) -> str:
        return 'STRING LITERAL [VALUE "{}"]'.format(self.value)

class VariableValueExpression(Expression):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'VARIABLE [VALUE: "{}"]'.format(self.name)

class ConditionExpression(Expression):
    def __init__(self,
                 condition: Expression,
                 true_expression: Expression,
                 false_expression: Expression) -> None:
        self.condition = condition
        self.true_expression = true_expression
        self.false_expression = false_expression

    def __repr__(self) -> str:
        return ("CONDITION [{}, TRUE: {}, FALSE: {}]"
                .format(self.condition, self.true_expression, self.false_expression))

class LoopExpression(Expression):
    def __init__(self, condition: Expression, body: list[Expression]) -> None:
        self.condition = condition
        self.body = body

    def __repr__(self) -> str:
        return "LOOP [CONDITION: {}, BODY: {}]".format(self.condition, self.body)

class FunctionDefinitionExpression(Expression):
    def __init__(self, name: str, parameters: list[str], body: list[Expression]) -> None:
        self.name = name
        self.parameters = parameters
        self.body = body

    def __repr__(self) -> str:
        return ('FUNCTION DEF [NAME: "{}", PARAMETERS: {}, BODY: {}]'
                .format(self.name, self.parameters, self.body))

class VariableAssignmentExpression(Expression):
    def __init__(self, name: str, value: Expression) -> None:
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return 'VARIABLE ASSIGNMENT [NAME: "{}", VALUE: {}]'.format(self.name, self.value)

class BinaryOperationExpression(Expression):
    def __init__(self, operator, first: Expression, second: Expression) -> None:
        self.operator = operator
        self.first = first
        self.second = second

    def __repr__(self) -> str:
        return 'BINARY OPERATION [OPERATOR: "{}", FIRST: {}, SECOND: {}]'.format(self.operator, self.first, self.second)

class UnaryOperatorExpression(Expression):
    def __init__(self) -> None:
        pass

class Parser:
    def __init__(self, tokens):
        self._tokens = tokens
        self._ptr = 0

    def _cur_token(self) -> Token:
        assert self._ptr < len(self._tokens), "Out of tokens"
        return self._tokens[self._ptr]

    def _next(self):
        self._ptr += 1

    def parse_expressions(self) -> list[Expression]:
        result = []
        while self._ptr != len(self._tokens) and self._cur_token().type != TokenType.CLOSE_BRACKET:
            result.append(self.parse_expression())
        return result

    def parse_expression(self) -> Expression:
        token = self._cur_token()
        if token.type == TokenType.OPEN_BRACKET:
            self._next()
            result = self.parse_bracketed_expression()
            token = self._cur_token()
            assert token.type == TokenType.CLOSE_BRACKET
            self._next()
            return result
        elif token.type == TokenType.VARNAME:
            self._next()
            return VariableValueExpression(token.value)
        elif token.type == TokenType.NUMBER_LITERAL:
            self._next()
            return NumberLiteralExpression(token.value)
        elif token.type == TokenType.STRING_LITERAL:
            self._next()
            return StringLiteralExpression(token.value)
        else:
            assert False, "Unexpected token {}".format(token)

    def parse_bracketed_expression(self) -> Expression:
        token = self._cur_token()
        if token.type == TokenType.VARNAME:
            return self.parse_function_call()
        elif token.type == TokenType.KEY_IF:
            return self.parse_if_condition()
        elif token.type == TokenType.KEY_DEFUN:
            return self.parse_function_definition()
        elif token.type == TokenType.KEY_SETQ:
            return self.parse_assignment()
        elif token.type in [TokenType.MOD, TokenType.AND, TokenType.OR, TokenType.PLUS,
                            TokenType.SUB, TokenType.MUL, TokenType.DIV, TokenType.EQUALS,
                            TokenType.LESS, TokenType.GREATER]:
            return self.parse_binary_operator()
        elif token.type == TokenType.KEY_LOOP:
            return self.parse_loop_expression()
        elif token.type == TokenType.NOT:
            assert False, "Not implemented"  # unary operation
        else:
            assert False, "Unexpected token"

    def parse_function_call(self) -> Expression:
        token = self._cur_token()
        self._next()
        args = self.parse_expressions()
        name = token.value
        return FunctionCallExpression(name, args)

    def parse_if_condition(self) -> Expression:
        token = self._cur_token()
        assert token.type == TokenType.KEY_IF
        self._next()
        condition = self.parse_expression()
        true = self.parse_expression()
        false = self.parse_expression()
        return ConditionExpression(condition, true, false)

    def parse_function_definition(self) -> Expression:
        assert self._cur_token().type == TokenType.KEY_DEFUN
        self._next()
        name = self._cur_token().value
        self._next()
        assert self._cur_token().type == TokenType.OPEN_BRACKET
        self._next()
        parameters = self.parse_function_parameters()
        assert self._cur_token().type == TokenType.CLOSE_BRACKET
        self._next()
        body = self.parse_expressions()
        return FunctionDefinitionExpression(name, parameters, body)

    def parse_function_parameters(self) -> list:
        result = []
        while self._cur_token().type != TokenType.CLOSE_BRACKET:
            token = self._cur_token()
            assert token.type == TokenType.VARNAME
            result.append(token.value)
            self._next()
        return result

    def parse_assignment(self) -> Expression:
        assert self._cur_token().type == TokenType.KEY_SETQ
        self._next()
        token = self._cur_token()
        assert token.type == TokenType.VARNAME
        name = token.value
        self._next()
        value = self.parse_expression()
        return VariableAssignmentExpression(name, value)

    def parse_binary_operator(self) -> Expression:
        assert self._cur_token().type in [
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
        ]
        operator = self._cur_token().type.value
        self._next()
        first_operand = self.parse_expression()
        second_operand = self.parse_expression()
        return BinaryOperationExpression(operator, first_operand, second_operand)

    def parse_loop_expression(self) -> Expression:
        assert self._cur_token().type == TokenType.KEY_LOOP
        self._next()
        condition = self.parse_expression()
        body = self.parse_expressions()
        return LoopExpression(condition, body)

def main():
    lex = Lexer("""
    ; comment
    (defun print-str(addr)
        (setq len (load addr))
        (setq i 0)
        (loop (= len i)
            (setq i (+ i 1))
            (put (load (+ addr i)))
        )
    )
    (print-str "Hello, world!")
    """)
    tokenz = []
    while True:
        token = lex.next()
        if token is None:
            break
        print(token)
        tokenz.append(token)
    ast = Parser(tokenz).parse_expressions()
    print(ast)

if __name__ == '__main__':
    main()
