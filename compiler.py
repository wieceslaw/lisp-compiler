from lexer import Lexer
from parsing import *


class DataSegment:
    def __init__(self, size):
        self.size = size
        self.cur = 0
        self.data = [0] * size

    def put_string(self, string: str) -> int:
        assert self.size - self.cur >= len(string)
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

    def layout(self) -> list:
        return self.data


class TextSegment:
    def __init__(self, size: int):
        self.size = size
        self.data = []

    def put(self, instructions: list) -> int:
        address = len(self.data)
        self.data.extend(instructions)
        return address


# nop <symbol>          % function definition
# call <symbol>         % function call
# setq <symbol> <value> % variable assignment
# <symbol>              % variable value

# nop (label) -> nop (0)
# call (symbol) -> call (address)
# address: absolute, relative($sf, $sp)

class Compiler:
    def __init__(self, root: RootExpression):
        self.text = TextSegment(4096)
        self.data = DataSegment(4096)
        self.root = root
        self.functions = self.extract_functions(self.root)

    def compile(self):
        root_variables = self.collect_variables(self.root, {})

        print("% ROOT VARS", root_variables)
        for expression in self.root.expressions:
            self.compile_expression(expression, root_variables)
            print("pop % clean up")
        for name, func in self.functions.items():
            function_variables = {func.parameters[i]: i for i in range(len(func.parameters))}
            self.collect_variables(func, function_variables)
            print("% FUNC [{}] VARS".format(name), function_variables)
            for expression in func.body:
                self.compile_expression(expression, function_variables)
                print("pop % clean up")

    def compile_global_scope(self, variables: list[str]):
        addresses = {}
        for variable in variables:
            address = self.data.put_variable()
            addresses[variable] = {"type": "absolute", "value": address}

    def compile_function_scope(self, expression: FunctionDefinitionExpression, variables: list[str]):
        addressed_variables = {}
        for i, variable in enumerate(variables):
            addressed_variables[variable] = {"type": "relative", "offset": i}
        for i, expression in enumerate(expression.body):
            self.compile_expression(expression, addressed_variables)
            if i != len(expression.body):
                print("pop % clean up")

    def extract_functions(self, root: RootExpression):
        def modifier(expression: Expression) -> Expression:
            if isinstance(expression, FunctionDefinitionExpression):
                functions[expression.name] = expression
                return NumberLiteralExpression(expression.token, 0)
            return expression

        functions = {}
        root.apply_traverse(modifier)
        return functions

    def collect_variables(self, expression: Expression, result: dict[str, int]):
        def extract_variables(e: Expression):
            if isinstance(e, FunctionCallExpression):
                pass
                # assert expression.name in self.functions, "UNKNOWN SYMBOL: {}".format(expression.token)
            elif isinstance(e, VariableValueExpression):
                assert e.name in result, "UNKNOWN SYMBOL: {}".format(expression.token)
            elif isinstance(e, VariableAssignmentExpression):
                if e.name not in result:
                    result[e.name] = len(result)
            return e

        expression.apply_traverse(extract_variables)
        return result

    def compile_expression(self, expression: Expression, variables: dict[str,]):
        if isinstance(expression, StringLiteralExpression):
            self.compile_string_literal(expression, variables)
        elif isinstance(expression, NumberLiteralExpression):
            self.compile_number_literal(expression, variables)
        elif isinstance(expression, VariableValueExpression):
            self.compile_variable_value_expression(expression, variables)
        elif isinstance(expression, VariableAssignmentExpression):
            self.compile_variable_assignment(expression, variables)
        elif isinstance(expression, FunctionCallExpression):
            self.compile_function_call(expression, variables)
        else:
            assert False, "NOT IMPLEMENTED [{}]".format(expression)

    def compile_variable_value_expression(self, expression: VariableValueExpression, variables: dict[str,]):
        lcvariable = {"type": "local",
                      "name": "a",
                      "offset": "0"}
        glvariable = {"type": "global",
                      "name": "b",
                      "address": 0x1234}
        variable = variables[expression.name]
        if variable["type"] == "local":
            print("push [{}] % load stack frame".format(variable["offset"]))
        elif variable["type"] == "global":
            print("push [{}] % load absolute".format(variable["address"]))
        else:
            assert False, "Unknown variable type"

    def compile_number_literal(self, expression: NumberLiteralExpression, variables: dict[str,]):
        print("push [{}] % number literal".format(expression.value))

    def compile_string_literal(self, expression: StringLiteralExpression, variables: dict[str,]):
        address = self.data.put_string(expression.value)
        print("push [{}] % string literal".format(address))

    def compile_variable_assignment(self, expression: VariableAssignmentExpression, variables: dict[str,]):
        assert expression.name in variables, "UNKNOWN VARIABLE {}".format(expression.token)
        self.compile_expression(expression.value, variables)
        variable = variables[expression.name]
        address = "address of {}".format(variable)  # TODO: Implement
        print("store [{}] % variable assignment".format(address))

    def compile_binary_operator(self, expression: BinaryOperationExpression, variables: dict[str,]):
        self.compile_expression(expression.first, variables)
        self.compile_expression(expression.second, variables)
        print("{} ; binary operator".format(expression.operator))
        print("swop")
        print("swop")

    def compile_function_call(self, expression: FunctionCallExpression, variables: dict[str,]):
        for argument in expression.arguments:
            self.compile_expression(argument, variables)
        print("call {} % function name symbol".format(expression.name))


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
    (zero)
    (defun zero()
        (setq i (setq j 1))
    )
    (zero)
    (setq a 1)
    (print-str "Hello, world!")
    """)

    tokens = []
    while True:
        token = lex.next()
        if token is None:
            break
        print(token)
        tokens.append(token)
    ast = Parser(tokens).parse()
    print(ast)
    compiler = Compiler(ast)
    print("============= COMPILATION ==============")
    compiler.compile()


if __name__ == '__main__':
    main()
