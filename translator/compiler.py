from machine.isa import Opcode, Addressing, Register
from lexer import Lexer
from parsing import *


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

    def put_one(self, instruction: dict) -> int:
        new_size = len(self.instructions) + 1
        assert new_size <= self.capacity, "Out of instruction memory"
        address = len(self.instructions)
        self.instructions.append(instruction)
        return address

    def put_many(self, instructions: list[dict]) -> int:
        new_size = len(self.instructions) + len(instructions)
        assert new_size <= self.capacity, "Out of instruction memory"
        address = len(self.instructions)
        for instruction in instructions:
            self.put_one(instruction)
        return address


class Compiler:
    def __init__(self, root: RootExpression):
        self.text_segment = TextSegment(4096)
        self.data_segment = DataSegment(4096)
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
            address = self.data_segment.put_word()
            variables[name] = {
                "type": Addressing.ABSOLUTE,
                "debug": "variable name: {}".format(name),
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
            variable_index = {function_expression.parameters[i]: i for i in range(len(function_expression.parameters))}
            self.collect_variables(function_expression, variable_index)
            variables = {}
            for index, name in enumerate(variable_index):
                variables[name] = {
                    "addressing": Addressing.RELATIVE,
                    "debug": "variable name: {}".format(name),
                    "register": Register.FRAME_POINTER,
                    "offset": index,  # TODO: +2?
                }
            functions[function_expression.name] = {
                "expression": function_expression,
                "variables": variable_index
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
        for instruction in self.text_segment.instructions:
            if instruction["opcode"] == Opcode.CALL:
                symbol = instruction["symbol"]
                instruction["address"] = self.symbol_table[symbol]

    def compile_root(self, root: RootExpression, global_variables: dict):
        self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "program start"})
        for expression in root.expressions:
            self.compile_expression(expression, global_variables)
            self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({"opcode": Opcode.HALT, "debug": "program end"})

    def compile_function(self, expression: FunctionDefinitionExpression, variables: dict[str, dict]):
        # TODO: Refactor, remove variable lengths and dicts
        function_address = self.text_segment.put_one({
            "opcode": Opcode.NOP,
            "debug": "SYMBOL [{}]".format(expression.name)
        })
        self.symbol_table[expression.name] = function_address
        local_variables_length = len(variables) - len(expression.parameters)
        for i in range(local_variables_length):
            self.text_segment.put_one({
                "opcode": Opcode.PUSH,
                "debug": "allocating local variable [{}]".format(i)
            })
        if len(expression.body) == 0:
            self.text_segment.put_one({"opcode": Opcode.PUSH, "debug": "garbage push"})
        for i, e in enumerate(expression.body):
            self.compile_expression(e, variables)
            if i != len(expression.body):
                self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            },
            "debug": "save result"
        })
        for i in range(local_variables_length):
            self.text_segment.put_one({"opcode": Opcode.POP, "debug": "clearing local variable [{}]".format(i)})
        self.text_segment.put_one({"opcode": Opcode.RET})

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
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": variable_address,
            "debug": "allocate for variable [{}]".format(expression.name)
        })
        self.text_segment.put_one({"opcode": Opcode.PUSH})
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })

    def compile_number_literal(self, expression: NumberLiteralExpression):
        static_address = self.data_segment.put_word(expression.value)
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.ABSOLUTE,
                "address": static_address
            },
            "debug": "number literal"
        })
        self.text_segment.put_one({"opcode": Opcode.PUSH})
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })

    def compile_string_literal(self, expression: StringLiteralExpression):
        static_address = self.data_segment.put_string(expression.value)
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.ABSOLUTE,
                "address": static_address
            },
            "debug": "string literal"
        })
        self.text_segment.put_one({"opcode": Opcode.PUSH})
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })

    def compile_variable_assignment(self, expression: VariableAssignmentExpression, variables: dict[str]):
        assert expression.name in variables, "Unknown variable [{}]".format(expression.token)
        self.compile_expression(expression.value, variables)
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })
        variable_address = variables[expression.name]
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": variable_address
        })

    def compile_allocation(self, expression: AllocationExpression):
        buffer_address = self.data_segment.allocate(expression.size)
        static_address = self.data_segment.put_word(buffer_address)
        self.text_segment.put_one({"opcode": Opcode.PUSH, "debug": "allocation of size: {}".format(expression.size)})
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.ABSOLUTE,
                "address": static_address
            },
        })

    def compile_function_call(self, expression: FunctionCallExpression, variables: dict[str]):
        for argument in expression.arguments:
            self.compile_expression(argument, variables)
        self.text_segment.put_one({
            "opcode": Opcode.CALL,
            "operand": None,
            "symbol": expression.name,
            "debug": "function call {}".format(expression.name)
        })
        for i in range(len(expression.arguments)):
            self.text_segment.put_one({"opcode": Opcode.POP, "debug": "local allocation clear"})
        self.text_segment.put_one({"opcode": Opcode.PUSH})
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })

    def compile_binary_operator(self, expression: BinaryOperationExpression, variables: dict[str]):
        self.compile_expression(expression.first, variables)
        self.compile_expression(expression.second, variables)
        binary_opcode = Opcode.from_binary_operator(expression.operator)
        if binary_opcode == Opcode.ST:
            self.text_segment.put_one({
                "opcode": Opcode.LD,
                "operand": {
                    "type": Addressing.RELATIVE,
                    "register": Register.STACK_POINTER,
                    "offset": +1
                },
                "debug": "load value"
            })
            self.text_segment.put_one({
                "opcode": binary_opcode,
                "operand": {
                    "type": Addressing.RELATIVE_INDIRECT,
                    "register": Register.STACK_POINTER,
                    "offset": +2
                },
                "debug": "store value"
            })
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
            self.text_segment.put_one({
                "opcode": Opcode.LD,
                "operand": first_operand,
                "debug": "load value"
            })
            self.text_segment.put_one({
                "opcode": binary_opcode,
                "operand": second_operand,
                "debug": "store value"
            })
        self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            },
            "debug": "put result of binary operator"
        })

    def compile_unary_operator(self, expression: UnaryOperatorExpression, variables: dict[str]):
        self.compile_expression(expression.operand, variables)
        unary_opcode = Opcode.from_unary_operator(expression.operator)
        if unary_opcode == Opcode.LD:
            self.text_segment.put_one({
                "opcode": unary_opcode,
                "operand": {
                    "type": Addressing.RELATIVE_INDIRECT,
                    "register": Register.STACK_POINTER,
                    "offset": +1
                },
                "debug": "load operation"
            })
        else:
            self.text_segment.put_one({
                "opcode": unary_opcode,
                "operand": {
                    "type": Addressing.RELATIVE,
                    "register": Register.STACK_POINTER,
                    "offset": +1
                },
                "debug": "load operation"
            })
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            },
            "debug": "put result of unary operator"
        })

    def compile_nullary_operator(self, expression: NullaryOperatorExpression):
        self.text_segment.put_one({"opcode": Opcode.PUSH, "debug": "allocate for nullary operation"})
        if expression.operator == TokenType.KEY_GET:
            self.text_segment.put_one({"opcode": Opcode.GET})
        else:
            assert False, "Unknown nullary operator"
        self.text_segment.put_one({
            "opcode": Opcode.ST,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            },
            "debug": "put result of nullary operator"
        })

    def compile_loop_expression(self, expression: LoopExpression, variables: dict[str]):
        loop_start_address = self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "loop start"})
        self.compile_expression(expression.condition, variables)
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })
        loop_after_instruction = {"opcode": Opcode.JZ, "operand": None, "debug": "jump out of loop"}
        self.text_segment.put_one(loop_after_instruction)
        for body_expression in expression.body:
            self.compile_expression(body_expression, variables)
            self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({"opcode": Opcode.JMP, "operand": loop_start_address, "debug": "jump loop begin"})
        loop_after_address = self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "loop after"})
        loop_after_instruction["address"] = loop_after_address

    def compile_condition(self, expression: ConditionExpression, variables: dict[str]):
        self.compile_expression(expression.condition, variables)
        self.text_segment.put_one({
            "opcode": Opcode.LD,
            "operand": {
                "type": Addressing.RELATIVE,
                "register": Register.STACK_POINTER,
                "offset": +1
            }
        })
        false_jump = {"opcode": Opcode.JZ, "address": None, "debug": "jump if false"}
        self.text_segment.put_one(false_jump)
        self.compile_expression(expression.true_expression, variables)
        true_jump_out = {"opcode": Opcode.JMP, "address": None}
        self.text_segment.put_one(true_jump_out)
        false_address = self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "if false"})
        self.compile_expression(expression.false_expression, variables)
        after_address = self.text_segment.put_one({
            "opcode": Opcode.LD,
            "address": {
                "type": Addressing.RELATIVE,
                "offset": +2,
                "register": Register.STACK_POINTER
            },
            "debug": "after if"
        })
        self.text_segment.put_one({"opcode": Opcode.POP})
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
    for i, instruction in enumerate(compiler.text_segment.instructions):
        print("{:3d}| {}".format(i, instruction))
    print(compiler.data_segment.data)


if __name__ == '__main__':
    main()
