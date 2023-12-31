from __future__ import annotations

from isa import Addressing, Opcode, Register
from lexer import TokenType
from parsing import (
    AllocationExpression,
    BinaryOperationExpression,
    ConditionExpression,
    EmptyExpression,
    Expression,
    FunctionCallExpression,
    FunctionDefinitionExpression,
    LoopExpression,
    NullaryOperatorExpression,
    NumberLiteralExpression,
    RootExpression,
    StringLiteralExpression,
    UnaryOperatorExpression,
    VariableAssignmentExpression,
    VariableValueExpression,
)


def unary_operators() -> dict[TokenType, Opcode]:
    return {TokenType.NOT: Opcode.NOT, TokenType.KEY_LOAD: Opcode.LD, TokenType.KEY_PUT: Opcode.PUT}


def comparison_operators() -> dict[TokenType, Opcode]:
    return {
        TokenType.EQUALS: Opcode.IS_ZERO,
        TokenType.GREATER: Opcode.IS_POS,
        TokenType.LESS: Opcode.IS_NEG,
    }


def arithmetic_operators() -> dict[TokenType, Opcode]:
    return {
        TokenType.AND: Opcode.AND,
        TokenType.OR: Opcode.OR,
        TokenType.PLUS: Opcode.ADD,
        TokenType.SUB: Opcode.SUB,
    }


class DataSegment:
    def __init__(self, capacity):
        self._capacity = capacity
        self._cur = 0
        self._data = [0] * capacity

    def put_string(self, string: str) -> int:
        assert self._capacity - self._cur >= len(string), "Limit of data memory exceeded"
        ref = self._cur
        self._data[self._cur] = len(string)
        self._cur += 1
        for i in range(len(string)):
            self._data[self._cur + i] = ord(string[i])
        self._cur += len(string)
        return ref

    def put_word(self, value: int = 0) -> int:
        assert self._capacity - self._cur >= 1, "Limit of data memory exceeded"
        self._data[self._cur] = value
        ref = self._cur
        self._cur += 1
        return ref

    def allocate(self, size: int) -> int:
        assert self._capacity - self._cur >= size, "Limit of data memory exceeded"
        ref = self._cur
        self._cur += size
        return ref

    def layout(self) -> list:
        return self._data[: self._cur]


class TextSegment:
    def __init__(self, capacity: int):
        self.instructions = []
        self._capacity = capacity

    def write_instruction(self, instruction: dict, debug: str | None = None) -> int:
        new_size = len(self.instructions) + 1
        assert new_size <= self._capacity, "Limit of instruction memory exceeded"
        address = len(self.instructions)
        if debug:
            instruction["debug"] = debug
        instruction["index"] = len(self.instructions)
        self.instructions.append(instruction)
        return address

    def write_instructions(self, instructions: list[dict]) -> int:
        new_size = len(self.instructions) + len(instructions)
        assert new_size <= self._capacity, "Limit of instruction memory exceeded"
        address = len(self.instructions)
        for instruction in instructions:
            self.write_instruction(instruction)
        return address

    def write_push(self, debug: str | None = None):
        return self.write_instruction({"opcode": Opcode.PUSH}, debug)

    def write_accumulator_push(self, debug: str | None = None):
        address = self.write_push(debug)
        self.write_instruction(
            {
                "opcode": Opcode.ST,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            }
        )
        return address

    def write_stack_load(self, debug=None):
        return self.write_instruction(
            {
                "opcode": Opcode.LD,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            },
            debug,
        )

    def write_nop(self, debug=None):
        return self.write_instruction({"opcode": Opcode.NOP}, debug)

    def write_pop(self, debug=None):
        return self.write_instruction({"opcode": Opcode.POP}, debug)


class Compiler:
    def __init__(self, root: RootExpression, data_max_size: int, text_max_size: int):
        self.data = DataSegment(data_max_size)
        self.text = TextSegment(text_max_size)
        self.root = root
        self.functions = self._filter_functions(self.root, self._extract_functions(root))
        self.symbol_table = {}

    def process(self):
        self._compile_root(self.root, self._root_variables(self.root))
        for function in self.functions.values():
            self._compile_function(function, self._function_variables(function))
        self._link()

    def _root_variables(self, root: RootExpression) -> dict[str, dict]:
        variable_index = self._collect_variables(root, {})
        variables = {}
        for name in variable_index:
            address = self.data.put_word()
            variables[name] = {
                "type": Addressing.ABSOLUTE,
                "value": address,
            }
        return variables

    def _function_variables(self, function: FunctionDefinitionExpression) -> dict[str, dict]:
        variables = {}
        parameter_index = {function.parameters[i]: i for i in range(len(function.parameters))}
        for index, name in enumerate(parameter_index):
            variables[name] = {
                "type": Addressing.RELATIVE,
                "register": Register.FRAME_POINTER,
                "offset": +2 - index + len(parameter_index),
            }
        locals_index = self._collect_variables(function, parameter_index)
        for index, name in enumerate(locals_index):
            variables[name] = {
                "type": Addressing.RELATIVE,
                "register": Register.FRAME_POINTER,
                "offset": -index,
            }
        return variables

    @staticmethod
    def _extract_functions(root: RootExpression) -> dict[str, FunctionDefinitionExpression]:
        def extractor(e: Expression) -> Expression:
            if isinstance(e, FunctionDefinitionExpression):
                functions[e.name] = e
                return NumberLiteralExpression(e.token, 0)
            return e

        functions = {}
        root.apply_traverse(extractor)
        return functions

    @staticmethod
    def _function_calls(expression: Expression) -> list[str]:
        def traverser(e: Expression) -> Expression:
            if isinstance(e, FunctionCallExpression):
                ls.append(e.name)
            return e

        ls = []
        expression.apply_traverse(traverser)
        return ls

    @staticmethod
    def _filter_functions(root: RootExpression, functions: dict[str, FunctionDefinitionExpression]):
        def dfs(e: FunctionDefinitionExpression):
            visited[e.name] = True
            calls = Compiler._function_calls(e)
            for name in calls:
                if not visited[name]:
                    dfs(functions[name])

        visited = {name: False for name in functions.keys()}
        for name in Compiler._function_calls(root):
            if not visited[name]:
                dfs(functions[name])
        return {name: func for name, func in functions.items() if visited[name]}

    def _collect_variables(self, expression: Expression, context: dict[str, int]) -> dict[str, int]:
        def _traverser(e: Expression):
            if isinstance(e, FunctionCallExpression):
                assert e.name in self.functions, "Unknown function symbol [{}]".format(e.token)
            elif isinstance(e, VariableValueExpression):
                assert e.name in variables or e.name in context, "Unknown variable symbol [{}]".format(e.token)
            elif isinstance(e, VariableAssignmentExpression):
                if e.name not in variables and e.name not in context:
                    variables[e.name] = len(variables)
            return e

        variables = {}
        expression.apply_traverse(_traverser)
        return variables

    def _link(self):
        for instruction in self.text.instructions:
            if instruction["opcode"] == Opcode.CALL:
                symbol = instruction["symbol"]
                instruction.pop("symbol")
                instruction["address"] = {"type": Addressing.CONTROL_FLOW, "value": self.symbol_table[symbol]}

    def _compile_root(self, root: RootExpression, variables: dict):
        self.text.write_nop(debug="program start")
        for expression in root.expressions:
            self._compile_expression(expression, variables)
            self.text.write_pop()
        self.text.write_instruction({"opcode": Opcode.HALT}, debug="program end")

    def _compile_function(self, expression: FunctionDefinitionExpression, variables: dict[str, dict]):
        function_address = self.text.write_nop(debug="function [{}]".format(expression.name))
        self.symbol_table[expression.name] = function_address
        local_variables_length = len(variables) - len(expression.parameters)
        for i in range(local_variables_length):
            self.text.write_push(debug="allocate local variable [{}]".format(i))
        if len(expression.body) == 0:
            self.text.write_push(debug="garbage push")
        for i, e in enumerate(expression.body):
            self._compile_expression(e, variables)
            if i != len(expression.body) - 1:
                self.text.write_pop()
        self.text.write_stack_load(debug="save result")
        self.text.write_pop("clear result")
        for i in range(local_variables_length):
            self.text.write_pop(debug="clear local variable [{}]".format(i))
        self.text.write_instruction({"opcode": Opcode.RET})

    def _compile_expression(self, expression: Expression, variables: dict[str, dict]):
        match expression:
            case StringLiteralExpression() as e:
                self._compile_string_literal(e)
            case NumberLiteralExpression() as e:
                self._compile_number_literal(e)
            case VariableValueExpression() as e:
                self._compile_variable_value_expression(e, variables)
            case VariableAssignmentExpression() as e:
                self._compile_variable_assignment(e, variables)
            case FunctionCallExpression() as e:
                self._compile_function_call(e, variables)
            case LoopExpression() as e:
                self._compile_loop_expression(e, variables)
            case BinaryOperationExpression() as e:
                self._compile_binary_operator(e, variables)
            case UnaryOperatorExpression() as e:
                self._compile_unary_operator(e, variables)
            case ConditionExpression() as e:
                self._compile_condition(e, variables)
            case NullaryOperatorExpression() as e:
                self._compile_nullary_operator(e)
            case AllocationExpression() as e:
                self._compile_allocation(e)
            case EmptyExpression():
                pass
            case _:
                assert False, "Not implemented [{}]".format(expression)

    def _compile_variable_value_expression(self, expression: VariableValueExpression, variables: dict[str, dict]):
        variable_address = variables[expression.name]
        self.text.write_instruction(
            {"opcode": Opcode.LD, "address": variable_address},
            debug="variable value [{}]".format(expression.name),
        )
        self.text.write_accumulator_push()

    def _compile_number_literal(self, expression: NumberLiteralExpression):
        static_address = self.data.put_word(expression.value)
        self.text.write_instruction(
            {"opcode": Opcode.LD, "address": {"type": Addressing.ABSOLUTE, "value": static_address}},
            debug="number literal [{}]".format(expression.value),
        )
        self.text.write_accumulator_push()

    def _compile_string_literal(self, expression: StringLiteralExpression):
        string_address = self.data.put_string(expression.value)
        static_address = self.data.put_word(string_address)
        self.text.write_instruction(
            {"opcode": Opcode.LD, "address": {"type": Addressing.ABSOLUTE, "value": static_address}},
            debug="string literal [{}]".format(expression.value),
        )
        self.text.write_accumulator_push()

    def _compile_variable_assignment(self, expression: VariableAssignmentExpression, variables: dict[str, dict]):
        assert expression.name in variables, "Unknown variable [{}]".format(expression.token)
        self._compile_expression(expression.value, variables)
        self.text.write_stack_load()
        variable_address = variables[expression.name]
        self.text.write_instruction({"opcode": Opcode.ST, "address": variable_address})

    def _compile_allocation(self, expression: AllocationExpression):
        buffer_address = self.data.allocate(expression.size)
        static_address = self.data.put_word(buffer_address)
        self.text.write_push(debug="allocation of size [{}]".format(expression.size))
        self.text.write_instruction(
            {"opcode": Opcode.LD, "address": {"type": Addressing.ABSOLUTE, "value": static_address}}
        )

    def _compile_function_call(self, expression: FunctionCallExpression, variables: dict[str, dict]):
        for argument in expression.arguments:
            self._compile_expression(argument, variables)
        self.text.write_instruction(
            {"opcode": Opcode.CALL, "address": None, "symbol": expression.name},
            debug="function call [{}]".format(expression.name),
        )
        for i in range(len(expression.arguments)):
            self.text.write_pop(debug="local allocation clear")
        self.text.write_accumulator_push()

    def _compile_binary_operator(self, expression: BinaryOperationExpression, variables: dict[str, dict]):
        if expression.operator == TokenType.KEY_STORE:
            self._compile_store_operator(expression, variables)
        elif expression.operator in comparison_operators():
            self._compile_comparison_operator(expression, variables)
        elif expression.operator in arithmetic_operators():
            self._compile_arithmetic_operator(expression, variables)
        else:
            assert False, "Unknown binary operator [{}]".format(expression.token)

    def _compile_arithmetic_operator(self, expression: BinaryOperationExpression, variables: dict[str, dict]):
        self._compile_expression(expression.first, variables)
        self._compile_expression(expression.second, variables)
        arithmetic_opcode = arithmetic_operators()[expression.operator]
        self.text.write_instruction(
            {
                "opcode": Opcode.LD,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +2},
            },
            debug="binary operation [{}]".format(expression.operator),
        )
        self.text.write_instruction(
            {
                "opcode": arithmetic_opcode,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            }
        )
        self.text.write_pop()
        self.text.write_instruction(
            {
                "opcode": Opcode.ST,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            }
        )

    def _compile_comparison_operator(self, expression: BinaryOperationExpression, variables: dict[str, dict]):
        assert expression.operator in comparison_operators()
        self._compile_expression(expression.first, variables)
        self._compile_expression(expression.second, variables)
        comparison_opcode = comparison_operators()[expression.operator]
        self.text.write_instruction(
            {
                "opcode": Opcode.LD,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +2},
            },
            debug="binary operation [{}]".format(expression.operator),
        )
        self.text.write_instruction(
            {
                "opcode": Opcode.SUB,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            }
        )
        self.text.write_instruction({"opcode": comparison_opcode})
        self.text.write_pop()
        self.text.write_instruction(
            {
                "opcode": Opcode.ST,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            }
        )

    def _compile_store_operator(self, expression: BinaryOperationExpression, variables: dict[str, dict]):
        assert expression.operator == TokenType.KEY_STORE
        self._compile_expression(expression.first, variables)
        self._compile_expression(expression.second, variables)
        self.text.write_instruction(
            {
                "opcode": Opcode.LD,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            },
            debug="binary operation [{}]".format(expression.operator),
        )
        self.text.write_instruction(
            {
                "opcode": Opcode.ST,
                "address": {"type": Addressing.RELATIVE_INDIRECT, "register": Register.STACK_POINTER, "offset": +2},
            }
        )
        self.text.write_pop()

    def _compile_unary_operator(self, expression: UnaryOperatorExpression, variables: dict[str, dict]):
        self._compile_expression(expression.operand, variables)
        unary_opcode = unary_operators()[expression.operator]
        if unary_opcode == Opcode.LD:
            self.text.write_instruction(
                {
                    "opcode": unary_opcode,
                    "address": {"type": Addressing.RELATIVE_INDIRECT, "register": Register.STACK_POINTER, "offset": +1},
                },
                debug="unary operation [{}]".format(expression.operator),
            )
        else:
            self.text.write_instruction(
                {
                    "opcode": unary_opcode,
                    "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
                },
                debug="unary operation [{}]".format(expression.operator),
            )
        self.text.write_instruction(
            {
                "opcode": Opcode.ST,
                "address": {"type": Addressing.RELATIVE, "register": Register.STACK_POINTER, "offset": +1},
            }
        )

    def _compile_nullary_operator(self, expression: NullaryOperatorExpression):
        if expression.operator == TokenType.KEY_GET:
            self.text.write_instruction({"opcode": Opcode.GET}, debug="nullary operator")
        else:
            assert False, "Unknown nullary operator"
        self.text.write_accumulator_push()

    def _compile_loop_expression(self, expression: LoopExpression, variables: dict[str, dict]):
        loop_start_address = self.text.write_nop(debug="loop start")
        self._compile_expression(expression.condition, variables)
        self.text.write_stack_load()
        loop_after_instruction = {"opcode": Opcode.JZ, "address": None}
        self.text.write_instruction(loop_after_instruction, debug="jump out of loop")
        self.text.write_pop(debug="clear compare")
        for body_expression in expression.body:
            self._compile_expression(body_expression, variables)
            self.text.write_pop()
        self.text.write_instruction(
            {"opcode": Opcode.JMP, "address": {"type": Addressing.CONTROL_FLOW, "value": loop_start_address}},
            debug="jump loop begin",
        )
        loop_after_address = self.text.write_nop(debug="loop after")
        loop_after_instruction["address"] = {"type": Addressing.CONTROL_FLOW, "value": loop_after_address}

    def _compile_condition(self, expression: ConditionExpression, variables: dict[str, dict]):
        self._compile_expression(expression.condition, variables)
        self.text.write_stack_load()
        false_jump = {"opcode": Opcode.JZ, "address": None}
        self.text.write_instruction(false_jump, debug="jump if false")
        self._compile_expression(expression.true_expression, variables)
        true_jump_out = {"opcode": Opcode.JMP, "address": None}
        self.text.write_instruction(true_jump_out)
        false_address = self.text.write_nop(debug="if false")
        self._compile_expression(expression.false_expression, variables)
        after_address = self.text.write_instruction(
            {
                "opcode": Opcode.ST,
                "address": {"type": Addressing.RELATIVE, "offset": +2, "register": Register.STACK_POINTER},
            },
            debug="after if",
        )
        self.text.write_pop()
        true_jump_out["address"] = {"type": Addressing.CONTROL_FLOW, "value": after_address}
        false_jump["address"] = {"type": Addressing.CONTROL_FLOW, "value": false_address}
