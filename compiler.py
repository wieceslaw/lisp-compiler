from isa import Opcode, Addressing, Register
from lexer import Lexer
from parsing import *


class DataSegment:
    def __init__(self, size):
        self.size = size
        self.cur = 0
        self.data = [0] * size

    def put_string(self, string: str) -> int:
        assert self.size - self.cur >= len(string), "Out of memory"
        ref = self.cur
        self.data[self.cur] = len(string)
        self.cur += 1
        for i in range(len(string)):
            self.data[self.cur + i] = ord(string[i])
        self.cur += len(string)
        return ref

    def put_variable(self) -> int:
        assert self.size - self.cur >= 1
        ref = self.cur
        self.cur += 1
        return ref

    def allocate(self, size: int) -> int:
        assert self.size - self.cur >= size, "Out of memory"
        ref = self.cur
        self.cur += size
        return ref

    def layout(self) -> list:
        return self.data


class TextSegment:
    # TODO: Out of memory (add size)
    def __init__(self):
        self.instructions = []

    def put_one(self, instruction: dict) -> int:
        address = len(self.instructions)
        self.instructions.append(instruction)
        return address

    def put_many(self, instructions: list[dict]) -> int:
        address = len(self.instructions)
        for instruction in instructions:
            self.put_one(instruction)
        return address


class Compiler:
    def __init__(self, root: RootExpression):
        self.text_segment = TextSegment()
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
            address = self.data_segment.put_variable()
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

    def compile_function(self, expression: FunctionDefinitionExpression, local_variables: dict[str, dict]):
        symbol_address = self.text_segment.put_one({
            "opcode": Opcode.NOP,
            "debug": "SYMBOL [{}]".format(expression.name)
        })
        self.symbol_table[expression.name] = symbol_address
        for i, e in enumerate(expression.body):
            self.compile_expression(e, local_variables)
            if i != len(expression.body):
                self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({"opcode": Opcode.RET})
        self.text_segment.put_one({
            "opcode": Opcode.LOAD,
            "address": {
                "type": Addressing.RELATIVE,
                "offset": len(local_variables),  # TODO: +-1? correct?
                "register": Register.FRAME_POINTER
            }
        })
        self.text_segment.put_one({"opcode": Opcode.POP})

    def compile_expression(self, expression: Expression, variables: dict[str,]):
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

    def compile_variable_value_expression(self, expression: VariableValueExpression, variables: dict[str,]):
        address = variables[expression.name]
        self.text_segment.put_one({
            "opcode": Opcode.PUSH,
            "address": address,
            "debug": "variable value"
        })

    def compile_number_literal(self, expression: NumberLiteralExpression):
        self.text_segment.put_one({
            "opcode": Opcode.PUSH,
            "address": {
                "type": Addressing.IMMEDIATE,
                "value": expression.value
            },
            "debug": "number literal"
        })

    def compile_string_literal(self, expression: StringLiteralExpression):
        address = self.data_segment.put_string(expression.value)
        self.text_segment.put_one({
            "opcode": Opcode.PUSH,
            "address": {
                "type": Addressing.IMMEDIATE,
                "value": address
            },
            "debug": "string literal"
        })

    def compile_variable_assignment(self, expression: VariableAssignmentExpression, variables: dict[str,]):
        assert expression.name in variables, "Unknown variable [{}]".format(expression.token)
        self.compile_expression(expression.value, variables)
        address = variables[expression.name]
        self.text_segment.put_one({"opcode": Opcode.STORE, "address": address})

    def compile_binary_operator(self, expression: BinaryOperationExpression, variables: dict[str,]):
        self.compile_expression(expression.first, variables)
        self.compile_expression(expression.second, variables)
        binary_operator_opcode = Opcode.from_binary_operator(expression.operator)
        if binary_operator_opcode == Opcode.STORE:
            self.text_segment.put_one({
                "opcode": binary_operator_opcode,
                "address": {
                    "type": Addressing.RELATIVE_INDIRECT,
                }
            })
        else:
            self.text_segment.put_one({"opcode": binary_operator_opcode})
        self.text_segment.put_one({
            "opcode": Opcode.LOAD,
            "address": {
                "type": Addressing.RELATIVE,
                "offset": +3,
                "register": Register.STACK_POINTER
            }
        })
        self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({"opcode": Opcode.POP})

    def compile_unary_operator(self, expression: UnaryOperatorExpression, variables: dict[str,]):
        self.compile_expression(expression.operand, variables)
        unary_operator_opcode = Opcode.from_unary_operator(expression.operator)
        if unary_operator_opcode == Opcode.LOAD:
            self.text_segment.put_one({
                "opcode": unary_operator_opcode,
                "address": {
                    "type": Addressing.RELATIVE_INDIRECT
                }
            })
        else:
            self.text_segment.put_one({"opcode": unary_operator_opcode})
        self.text_segment.put_one({
            "opcode": Opcode.LOAD,
            "address": {
                "type": Addressing.RELATIVE,
                "offset": +2,
                "register": Register.STACK_POINTER
            }
        })
        self.text_segment.put_one({"opcode": Opcode.POP})

    def compile_nullary_operator(self, expression: NullaryOperatorExpression):
        nullary_operator_opcode = Opcode.from_nullary_operator(expression.operator)
        self.text_segment.put_one({"opcode": nullary_operator_opcode})

    def compile_function_call(self, expression: FunctionCallExpression, variables: dict[str,]):
        local_variables = self.functions[expression.name]["variables"]
        arguments_length = len(expression.arguments)
        locals_length = len(local_variables) - arguments_length
        self.text_segment.put_one({
            "opcode": Opcode.PUSH,
            "address": {
                "type": Addressing.IMMEDIATE,
                "value": 0
            },
            "debug": "return value allocation"
        })
        for i in range(locals_length):
            self.text_segment.put_one({
                "opcode": Opcode.PUSH,
                "address": {
                    "type": Addressing.IMMEDIATE,
                    "value": 0
                },
                "debug": "local variable allocation"
            })
        for argument in expression.arguments:
            self.compile_expression(argument, variables)
        self.text_segment.put_one({
            "opcode": Opcode.CALL,
            "address": None,
            "symbol": expression.name
        })
        for i in range(locals_length):
            self.text_segment.put_one({"opcode": Opcode.POP, "debug": "local allocation clear"})

    def compile_loop_expression(self, expression: LoopExpression, variables: dict[str,]):
        loop_start_address = self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "loop start"})
        self.compile_expression(expression.condition, variables)
        loop_after_instruction = {"opcode": Opcode.JZ, "address": None}
        self.text_segment.put_one(loop_after_instruction)
        for body_expression in expression.body:
            self.compile_expression(body_expression, variables)
            self.text_segment.put_one({"opcode": Opcode.POP})
        self.text_segment.put_one({
            "opcode": Opcode.JMP,
            "address": loop_start_address
        })
        loop_after_address = self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "loop after"})
        loop_after_instruction["address"] = loop_after_address

    def compile_condition(self, expression: ConditionExpression, variables: dict[str,]):
        self.compile_expression(expression.condition, variables)
        false_jump = {"opcode": Opcode.JZ, "address": None, "debug": "jump false"}
        self.text_segment.put_one(false_jump)
        self.compile_expression(expression.true_expression, variables)
        true_jump_out = {"opcode": Opcode.JMP, "address": None}
        self.text_segment.put_one(true_jump_out)
        false_address = self.text_segment.put_one({"opcode": Opcode.NOP, "debug": "if-false"})
        self.compile_expression(expression.false_expression, variables)
        after_address = self.text_segment.put_one({
            "opcode": Opcode.LOAD,
            "address": {
                "type": Addressing.RELATIVE,
                "offset": +2,
                "register": Register.STACK_POINTER
            },
            "debug": "if-after"
        })
        self.text_segment.put_one({"opcode": Opcode.POP})
        true_jump_out["address"] = after_address
        false_jump["address"] = false_address

    def compile_allocation(self, expression: AllocationExpression):
        buffer_address = self.data_segment.allocate(expression.size)
        self.text_segment.put_one({
            "opcode": Opcode.PUSH,
            "address": {
                "type": Addressing.IMMEDIATE,
                "value": buffer_address
            },
            "debug": "allocation of size: {}".format(expression.size)
        })


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
