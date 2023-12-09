from __future__ import annotations

from typing import Callable

from lexer import Token, TokenType, binary_operators, nullary_operators, unary_operators


class Expression:
    def __init__(self, token: Token):
        self.token = token

    def children(self) -> list[Expression]:
        return []

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        return

    def apply_traverse(self, f: Callable[[Expression], Expression]):
        self.apply(f)
        for node in self.children():
            node.apply_traverse(f)


class RootExpression(Expression):
    def __init__(self, expressions: list[Expression]):
        super().__init__(None)
        self.expressions = expressions

    def __repr__(self) -> str:
        return f"ROOT [{self.expressions}]"

    def children(self) -> list[Expression]:
        return self.expressions

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.expressions = list(map(f, self.expressions))


class FunctionCallExpression(Expression):
    def __init__(self, token: Token, name: str, arguments: list[Expression]):
        super().__init__(token)
        self.name = name
        self.arguments = arguments

    def __repr__(self) -> str:
        return 'FUNCTION CALL [NAME: "{}", ARGUMENTS: {}]'.format(self.name, self.arguments)

    def children(self) -> list[Expression]:
        return self.arguments

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.arguments = list(map(f, self.arguments))


class NumberLiteralExpression(Expression):
    def __init__(self, token: Token, value: int):
        super().__init__(token)
        self.value = value

    def __repr__(self) -> str:
        return 'NUMBER LITERAL [VALUE: "{}"]'.format(self.value)


class StringLiteralExpression(Expression):
    def __init__(self, token: Token, value: str):
        super().__init__(token)
        self.value = value

    def __repr__(self) -> str:
        return 'STRING LITERAL [VALUE "{}"]'.format(self.value)


class CharacterLiteralExpression(Expression):
    def __init__(self, token: Token, value: str):
        super().__init__(token)
        self.value = value

    def __repr__(self) -> str:
        return 'CHARACTER LITERAL [VALUE "{}"]'.format(self.value)


class VariableValueExpression(Expression):
    def __init__(self, token: Token, name: str):
        super().__init__(token)
        self.name = name

    def __repr__(self):
        return 'VARIABLE [VALUE: "{}"]'.format(self.name)


class ConditionExpression(Expression):
    def __init__(
        self, token: Token, condition: Expression, true_expression: Expression, false_expression: Expression
    ) -> None:
        super().__init__(token)
        self.condition = condition
        self.true_expression = true_expression
        self.false_expression = false_expression

    def __repr__(self) -> str:
        return "CONDITION [{}, TRUE: {}, FALSE: {}]".format(self.condition, self.true_expression, self.false_expression)

    def children(self) -> list[Expression]:
        return [self.condition, self.true_expression, self.false_expression]

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.condition = f(self.condition)
        self.true_expression = f(self.true_expression)
        self.false_expression = f(self.false_expression)


class LoopExpression(Expression):
    def __init__(self, token: Token, condition: Expression, body: list[Expression]) -> None:
        super().__init__(token)
        self.condition = condition
        self.body = body

    def __repr__(self) -> str:
        return "LOOP [CONDITION: {}, BODY: {}]".format(self.condition, self.body)

    def children(self) -> list[Expression]:
        return [self.condition, *self.body]

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.body = list(map(f, self.body))
        self.condition = f(self.condition)


class FunctionDefinitionExpression(Expression):
    def __init__(self, token: Token, name: str, parameters: list[str], body: list[Expression]) -> None:
        super().__init__(token)
        self.name = name
        self.parameters = parameters
        self.body = body

    def __repr__(self) -> str:
        return 'FUNCTION DEF [NAME: "{}", PARAMETERS: {}, BODY: {}]'.format(self.name, self.parameters, self.body)

    def children(self) -> list[Expression]:
        return self.body

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.body = list(map(f, self.body))


class VariableAssignmentExpression(Expression):
    def __init__(self, token: Token, name: str, value: Expression) -> None:
        super().__init__(token)
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return 'VARIABLE ASSIGNMENT [NAME: "{}", VALUE: {}]'.format(self.name, self.value)

    def children(self) -> list[Expression]:
        return [self.value]

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.value = f(self.value)


class BinaryOperationExpression(Expression):
    def __init__(self, token: Token, operator: TokenType, first: Expression, second: Expression) -> None:
        super().__init__(token)
        self.operator = operator
        self.first = first
        self.second = second

    def __repr__(self) -> str:
        return 'BINARY OPERATION [OPERATOR: "{}", FIRST: {}, SECOND: {}]'.format(self.operator, self.first, self.second)

    def children(self) -> list[Expression]:
        return [self.first, self.second]

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.first = f(self.first)
        self.second = f(self.second)


class UnaryOperatorExpression(Expression):
    def __init__(self, token: Token, operator: TokenType, operand: Expression) -> None:
        super().__init__(token)
        self.operator = operator
        self.operand = operand

    def __repr__(self) -> str:
        return 'UNARY OPERATION [OPERATOR: "{}", OPERAND: {}]'.format(self.operator, self.operand)

    def children(self) -> list[Expression]:
        return [self.operand]

    def apply(self, f: Callable[[Expression], Expression]) -> None:
        self.operand = f(self.operand)


class NullaryOperatorExpression(Expression):
    def __init__(self, token: Token, operator: TokenType) -> None:
        super().__init__(token)
        self.operator = operator

    def __repr__(self) -> str:
        return 'NULLARY OPERATION [OPERATOR: "{}"]'.format(self.operator)


class AllocationExpression(Expression):
    def __init__(self, token: Token, size: int) -> None:
        super().__init__(token)
        self.size = size

    def __repr__(self) -> str:
        return "MEMORY ALLOCATION [SIZE: {}]".format(self.size)


class EmptyExpression(Expression):
    def __init__(self, token: Token) -> None:
        super().__init__(token)


class Parser:
    def __init__(self, tokens):
        self._tokens = tokens
        self._ptr = 0

    def _cur_token(self) -> Token:
        assert self._ptr < len(self._tokens), "Out of tokens"
        return self._tokens[self._ptr]

    def _next(self):
        self._ptr += 1

    def parse(self) -> RootExpression:
        return RootExpression(self._parse_expressions())

    def _parse_expressions(self) -> list[Expression]:
        result = []
        while self._ptr != len(self._tokens) and self._cur_token().type != TokenType.CLOSE_BRACKET:
            result.append(self._parse_expression())
        return result

    def _parse_expression(self) -> Expression:
        token = self._cur_token()
        if token.type == TokenType.OPEN_BRACKET:
            self._next()
            result = self._parse_bracketed_expression()
            token = self._cur_token()
            assert token.type == TokenType.CLOSE_BRACKET
            self._next()
            return result
        if token.type == TokenType.VARNAME:
            self._next()
            return VariableValueExpression(token, token.value)
        if token.type == TokenType.NUMBER_LITERAL:
            self._next()
            return NumberLiteralExpression(token, token.value)
        if token.type == TokenType.STRING_LITERAL:
            self._next()
            return StringLiteralExpression(token, token.value)
        if token.type == TokenType.CHARACTER_LITERAL:
            self._next()
            return CharacterLiteralExpression(token, token.value)
        assert False, "Unexpected token {}".format(token)

    def _parse_bracketed_expression(self) -> Expression:
        token = self._cur_token()
        match token.type:
            case TokenType.VARNAME:
                return self._parse_function_call()
            case TokenType.KEY_IF:
                return self._parse_if_condition()
            case TokenType.KEY_DEFUN:
                return self._parse_function_definition()
            case TokenType.KEY_SETQ:
                return self._parse_assignment()
            case TokenType.KEY_LOOP:
                return self._parse_loop_expression()
            case TokenType.KEY_ALLOC:
                return self._parse_allocation()
            case _:
                if token.type in binary_operators():
                    return self._parse_binary_operator()
                if token.type in unary_operators():
                    return self._parse_unary_operator()
                if token.type in nullary_operators():
                    return self._parse_nullary_operator()
        assert False, "Unexpected token"

    def _parse_function_call(self) -> Expression:
        token = self._cur_token()
        self._next()
        args = self._parse_expressions()
        name = token.value
        return FunctionCallExpression(token, name, args)

    def _parse_if_condition(self) -> Expression:
        token = self._cur_token()
        assert token.type == TokenType.KEY_IF
        self._next()
        condition = self._parse_expression()
        true = self._parse_expression()
        false = self._parse_expression()
        return ConditionExpression(token, condition, true, false)

    def _parse_function_definition(self) -> Expression:
        token = self._cur_token()
        assert token.type == TokenType.KEY_DEFUN
        self._next()
        name = self._cur_token().value
        self._next()
        assert self._cur_token().type == TokenType.OPEN_BRACKET
        self._next()
        parameters = self._parse_function_parameters()
        assert self._cur_token().type == TokenType.CLOSE_BRACKET
        self._next()
        body = self._parse_expressions()
        return FunctionDefinitionExpression(token, name, parameters, body)

    def _parse_function_parameters(self) -> list:
        result = []
        while self._cur_token().type != TokenType.CLOSE_BRACKET:
            token = self._cur_token()
            assert token.type == TokenType.VARNAME
            result.append(token.value)
            self._next()
        return result

    def _parse_assignment(self) -> Expression:
        assert self._cur_token().type == TokenType.KEY_SETQ
        self._next()
        token = self._cur_token()
        assert token.type == TokenType.VARNAME
        name = token.value
        self._next()
        value = self._parse_expression()
        return VariableAssignmentExpression(token, name, value)

    def _parse_binary_operator(self) -> Expression:
        token = self._cur_token()
        assert token.type in binary_operators()
        operator = token.type.value
        self._next()
        first_operand = self._parse_expression()
        second_operand = self._parse_expression()
        return BinaryOperationExpression(token, operator, first_operand, second_operand)

    def _parse_unary_operator(self) -> Expression:
        token = self._cur_token()
        assert token.type in unary_operators()
        operator = token.type.value
        self._next()
        operand = self._parse_expression()
        return UnaryOperatorExpression(token, operator, operand)

    def _parse_nullary_operator(self) -> Expression:
        token = self._cur_token()
        assert token.type in nullary_operators()
        self._next()
        return NullaryOperatorExpression(token, token.type)

    def _parse_loop_expression(self) -> Expression:
        token = self._cur_token()
        assert token.type == TokenType.KEY_LOOP
        self._next()
        condition = self._parse_expression()
        body = self._parse_expressions()
        return LoopExpression(token, condition, body)

    def _parse_allocation(self) -> Expression:
        token = self._cur_token()
        assert token.type == TokenType.KEY_ALLOC
        self._next()
        token = self._cur_token()
        assert token.type == TokenType.NUMBER_LITERAL
        self._next()
        return AllocationExpression(token, token.value)
