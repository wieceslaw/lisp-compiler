from machine.isa import Opcode, Addressing, Register
from lexer import Lexer
from parsing import *


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


def from_unary_operator(token: TokenType):
    assert token in unary_operators(), "Unknown unary operator: {}".format(token)
    return {
        TokenType.NOT: Opcode.NOT,
        TokenType.KEY_LOAD: Opcode.LD,
        TokenType.KEY_PUT: Opcode.PUT
    }[token]


class DataSegment:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cur = 0
        self.data = [0] * capacity

    def put_string(self, string: str) -> int:
        assert self.capacity - self.cur >= len(string), "Out of data memory"
        ref = self.cur
        self.data[self.cur] = len(string)
        self.cur += 1
        for i in range(len(string)):
            self.data[self.cur + i] = ord(string[i])
        self.cur += len(string)
        return ref

    def put_word(self, value: int = 0) -> int:
        assert self.capacity - self.cur >= 1
        self.data[self.cur] = value
        ref = self.cur
        self.cur += 1
        return ref

    def allocate(self, size: int) -> int:
        assert self.capacity - self.cur >= size, "Out of data memory"
        ref = self.cur
        self.cur += size
        return ref

    def layout(self) -> list:
        return self.data


class TextSegment:
    def __init__(self, capacity: int):
        self.instructions = []
        self.capacity = capacity

    def write_instruction(self, instruction: dict, debug: str = None) -> int:
        new_size = len(self.instructions) + 1
        assert new_size <= self.capacity, "Out of instruction memory"
        address = len(self.instructions)
        if debug:
            instruction["debug"] = debug
        self.instructions.append(instruction)
        return address

    def write_instructions(self, instructions: list[dict]) -> int:
        new_size = len(self.instructions) + len(instructions)
        assert new_size <= self.capacity, "Out of instruction memory"
        address = len(self.instructions)
        for instruction in instructions:
            self.write_instruction(instruction)
        return address

    def write_push(self, debug: str = None):
        return self.write_instruction({"opcode": Opcode.PUSH}, debug)

    def write_accumulator_push(self, debug: str = None):
        address = self.write_push(debug)
        self.write_instruction({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })
        return address

    def write_stack_load(self, debug=None):
        return self.write_instruction({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        }, debug)

    def write_nop(self, debug=None):
        return self.write_instruction({"opcode": Opcode.NOP}, debug)

    def write_pop(self, debug=None):
        return self.write_instruction({"opcode": Opcode.POP}, debug)


class Compiler:
    def __init__(self, root: RootExpression):
        self.text = TextSegment(4096)
        self.data = DataSegment(4096)
        self.functions = self.preprocess_functions(root)
        self.root = self.preprocess_root(root)
        self.symbol_table = {}

    def compile(self):
        for function in self.functions.values():
            self.compile_function(function["expression"], function["variables"])
        self.compile_root(self.root["expression"], self.root["variables"])
        self.link()

    def preprocess_root(self, root: RootExpression) -> dict:
        """
        Извлекает глобальные переменные
        """
        variable_index = self.collect_variables(root, {})
        variables = {}
        for name in variable_index:
            address = self.data.put_word()
            variables[name] = {
                "type": Addressing.ABSOLUTE,
                "value": address,
            }
        return {
            "expression": root,
            "variables": variables
        }

    def preprocess_functions(self, root: RootExpression) -> dict[str, dict]:
        """
        Извлекает функции из корневого выражения;
        Индексирует локальные переменные и параметры функций;
        """
        function_expressions = self.extract_functions(root)
        functions = {}
        for function_expression in function_expressions:
            # TODO: differentiate local variables and parameters
            # TODO: but still check variable scope!
            variable_index = {function_expression.parameters[i]: i for i in range(len(function_expression.parameters))}
            self.collect_variables(function_expression, variable_index)
            variables = {}
            for index, name in enumerate(variable_index):
                variables[name] = {
                    "addressing": Addressing.RELATIVE,
                    "register": Register.FRAME_POINTER,
                    "offset": index,  # TODO: correct offset?
                }
            functions[function_expression.name] = {
                "expression": function_expression,
                "variables": variables
            }
        return functions

    def extract_functions(self, root: RootExpression) -> list[FunctionDefinitionExpression]:
        def extractor(expression: Expression) -> Expression:
            if isinstance(expression, FunctionDefinitionExpression):
                functions.append(expression)
                return NumberLiteralExpression(expression.token, 0)
            return expression

        functions = []
        root.apply_traverse(extractor)
        return functions

    def collect_variables(self, expression: Expression, result: dict[str, int]) -> dict[str, int]:
        def extract_variables(e: Expression):
            if isinstance(e, FunctionCallExpression):
                assert e.name in self.functions, "Unknown function symbol [{}]".format(e.token)
            elif isinstance(e, VariableValueExpression):
                assert e.name in result, "Unknown variable symbol [{}]".format(e.token)
            elif isinstance(e, VariableAssignmentExpression):
                if e.name not in result:
                    result[e.name] = len(result)
            return e

        expression.apply_traverse(extract_variables)
        return result

    def link(self):
        for instruction in self.text.instructions:
            if instruction["opcode"] == Opcode.CALL:
                symbol = instruction["symbol"]
                instruction.pop("symbol")
                instruction["operand"] = self.symbol_table[symbol]

    def compile_root(self, root: RootExpression, variables: dict):
        self.text.write_nop("program start")
        for expression in root.expressions:
            self.compile_expression(expression, variables)
            self.text.write_pop()
        self.text.write_instruction({"opcode": Opcode.HALT, "debug": "program end"})

    def compile_function(self, expression: FunctionDefinitionExpression, variables: dict[str, dict]):
        function_address = self.text.write_nop(debug="SYMBOL [{}]".format(expression.name))
        self.symbol_table[expression.name] = function_address
        local_variables_length = len(variables) - len(expression.parameters)
        for i in range(local_variables_length):
            self.text.write_push(debug="allocating local variable [{}]".format(variables))
        if len(expression.body) == 0:
            self.text.write_push(debug="garbage push")
        for i, e in enumerate(expression.body):
            self.compile_expression(e, variables)
            if i != len(expression.body):
                self.text.write_pop()
        self.text.write_stack_load(debug="save result")
        for i in range(local_variables_length):
            self.text.write_pop(debug="clearing local variable [{}]".format(i))
        self.text.write_instruction({"opcode": Opcode.RET})

    def compile_expression(self, expression: Expression, variables: dict[str]):
        if isinstance(expression, StringLiteralExpression):
            self.compile_string_literal(expression)
        elif isinstance(expression, NumberLiteralExpression):
            self.compile_number_literal(expression)
        elif isinstance(expression, VariableValueExpression):
            self.compile_variable_value_expression(expression, variables)
        elif isinstance(expression, VariableAssignmentExpression):
            self.compile_variable_assignment(expression, variables)
        elif isinstance(expression, FunctionCallExpression):
            self.compile_function_call(expression, variables)
        elif isinstance(expression, LoopExpression):
            self.compile_loop_expression(expression, variables)
        elif isinstance(expression, BinaryOperationExpression):
            self.compile_binary_operator(expression, variables)
        elif isinstance(expression, UnaryOperatorExpression):
            self.compile_unary_operator(expression, variables)
        elif isinstance(expression, ConditionExpression):
            self.compile_condition(expression, variables)
        elif isinstance(expression, NullaryOperatorExpression):
            self.compile_nullary_operator(expression)
        elif isinstance(expression, AllocationExpression):
            self.compile_allocation(expression)
        else:
            assert False, "Not implemented [{}]".format(expression)

    def compile_variable_value_expression(self, expression: VariableValueExpression, variables: dict[str]):
        variable_address = variables[expression.name]
        self.text.write_instruction({
            "opcode": Opcode.LD,
            "operand": variable_address
        }, debug="load variable value [{}]".format(expression.name))
        self.text.write_accumulator_push()

    def compile_number_literal(self, expression: NumberLiteralExpression):
        static_address = self.data.put_word(expression.value)
        self.text.write_instruction({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.ABSOLUTE,
                "address": static_address
            }
        }, debug="number literal")
        self.text.write_accumulator_push()

    def compile_string_literal(self, expression: StringLiteralExpression):
        static_address = self.data.put_string(expression.value)
        self.text.write_instruction({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.ABSOLUTE,
                "address": static_address
            }
        }, debug="string literal")
        self.text.write_accumulator_push()

    def compile_variable_assignment(self, expression: VariableAssignmentExpression, variables: dict[str]):
        assert expression.name in variables, "Unknown variable [{}]".format(expression.token)
        self.compile_expression(expression.value, variables)
        self.text.write_stack_load()
        variable_address = variables[expression.name]
        self.text.write_instruction({
            "opcode": Opcode.ST,
            "operand": variable_address
        })

    def compile_allocation(self, expression: AllocationExpression):
        buffer_address = self.data.allocate(expression.size)
        static_address = self.data.put_word(buffer_address)
        self.text.write_push(debug="allocation of size: {}".format(expression.size))
        self.text.write_instruction({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.ABSOLUTE,
                "address": static_address
            }
        })

    def compile_function_call(self, expression: FunctionCallExpression, variables: dict[str]):
        for argument in expression.arguments:
            self.compile_expression(argument, variables)
        self.text.write_instruction({
            "opcode": Opcode.CALL,
            "operand": None,
            "symbol": expression.name
        }, debug="function call [{}]".format(expression.name))
        for i in range(len(expression.arguments)):
            self.text.write_pop(debug="local allocation clear")
        self.text.write_accumulator_push()

    def compile_binary_operator(self, expression: BinaryOperationExpression, variables: dict[str]):
        self.compile_expression(expression.first, variables)
        self.compile_expression(expression.second, variables)
        binary_opcode = from_binary_operator(expression.operator)
        if binary_opcode == Opcode.ST:
            self.text.write_instruction({
                "opcode": Opcode.LD,
                "operand": {
                    "type": Addressing.RELATIVE,
                    "register": Register.STACK_POINTER,
                    "offset": +1
                }
            }, debug="load value")
            self.text.write_instruction({
                "opcode": binary_opcode,
                "operand": {
                    "type": Addressing.RELATIVE_INDIRECT,
                    "register": Register.STACK_POINTER,
                    "offset": +2
                }
            }, debug="store value")
        else:
            first_operand = {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +2
            }
            second_operand = {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
            self.text.write_instruction({
                "opcode": Opcode.LD,
                "operand": first_operand
            }, debug="load value")
            self.text.write_instruction({
                "opcode": binary_opcode,
                "operand": second_operand
            }, debug="store value")
        self.text.write_pop()
        self.text.write_instruction({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        }, debug="put result of binary operator")

    def compile_unary_operator(self, expression: UnaryOperatorExpression, variables: dict[str]):
        self.compile_expression(expression.operand, variables)
        unary_opcode = from_unary_operator(expression.operator)
        if unary_opcode == Opcode.LD:
            self.text.write_instruction({
                "opcode": unary_opcode,
                "operand": {
                    "type": Addressing.RELATIVE_INDIRECT,
                    "register": Register.STACK_POINTER,
                    "offset": +1
                }
            }, debug="load operation")
        else:
            self.text.write_instruction({
                "opcode": unary_opcode,
                "operand": {
                    "type": Addressing.RELATIVE,
                    "register": Register.STACK_POINTER,
                    "offset": +1
                }
            }, debug="load operation")
        self.text.write_instruction({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        }, debug="put result of unary operator")

    def compile_nullary_operator(self, expression: NullaryOperatorExpression):
        self.text.write_push(debug="allocate stack for nullary operation")
        if expression.operator == TokenType.KEY_GET:
            self.text.write_instruction({"opcode": Opcode.GET})
        else:
            assert False, "Unknown nullary operator"
        self.text.write_instruction({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        }, debug="put result of nullary operator")

    def compile_loop_expression(self, expression: LoopExpression, variables: dict[str]):
        loop_start_address = self.text.write_nop(debug="loop start")
        self.compile_expression(expression.condition, variables)
        self.text.write_stack_load()
        loop_after_instruction = {"opcode": Opcode.JZ, "operand": None}
        self.text.write_instruction(loop_after_instruction, debug="jump out of loop")
        for body_expression in expression.body:
            self.compile_expression(body_expression, variables)
            self.text.write_pop()
        self.text.write_instruction({"opcode": Opcode.JMP, "operand": loop_start_address}, debug="jump loop begin")
        loop_after_address = self.text.write_nop(debug="loop after")
        loop_after_instruction["address"] = loop_after_address

    def compile_condition(self, expression: ConditionExpression, variables: dict[str]):
        self.compile_expression(expression.condition, variables)
        self.text.write_stack_load()
        false_jump = {"opcode": Opcode.JZ, "address": None}
        self.text.write_instruction(false_jump, debug="jump if false")
        self.compile_expression(expression.true_expression, variables)
        true_jump_out = {"opcode": Opcode.JMP, "address": None}
        self.text.write_instruction(true_jump_out)
        false_address = self.text.write_nop(debug="if false")
        self.compile_expression(expression.false_expression, variables)
        after_address = self.text.write_instruction({
            "opcode": Opcode.LD,
            "address": {
                "type": Addressing.RELATIVE,
                "offset": +2,
                "register": Register.STACK_POINTER
            }
        }, debug="after if")
        self.text.write_pop()
        true_jump_out["address"] = after_address
        false_jump["address"] = false_address


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
    ; cat -- печатать данные, поданные на вход симулятору через файл ввода
    (setq char (get))
    (loop (not (= 0 char))      ; EOF == 0
        (put char)              ; put = print char, get = read char
        (setq char (get))
    )
    (print-str "Hello, world!")
    (defun is-multiple (n)
        (or
            (= 0 (mod n 5))
            (= 0 (mod n 3))
        )
    )
    (setq sum 0)
    (setq i 1)
    (loop (< i 1000)
        (setq i (- 1 i))
        (if (is-multiple i) (setq sum (+ sum i)) 0)
    )
    (setq buffer2 (alloc 128))
    (setq buffer1 (alloc 128))
    (store buffer1 'a')
    """)

    print("============= LEXING ==============")
    tokens = []
    while True:
        token = lex.next()
        if token is None:
            break
        print(token)
        tokens.append(token)
    print("============= PARSING ==============")
    ast = Parser(tokens).parse()
    print(ast)
    print("============= COMPILING ==============")
    compiler = Compiler(ast)
    compiler.compile()
    for i, instruction in enumerate(compiler.text.instructions):
        print("{:3d}| {}".format(i, instruction))
    print(compiler.data.data)


if __name__ == '__main__':
    main()
