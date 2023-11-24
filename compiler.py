from lexer import Lexer
from parsing import *


# располагает статические данные в сегменте данных
class DataSegment:
    def __init__(self, size):
        self.size = size
        self.cur = 0
        self.data = [0] * size

    def put_string(self, string: str) -> int:
        if self.size - self.cur < len(string):
            return -1
        ref = self.cur
        self.data[self.cur] = len(string)
        self.cur += 1
        for i in range(len(string)):
            self.data[self.cur + i] = ord(string[i])
        self.cur += len(string)
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

class Compiler:
    def __init__(self):
        self.text = TextSegment(4096)
        self.data = DataSegment(4096)
        self.root = None
        self.functions = dict()

    def compile(self):
        pass

    def compile_function(self, function: FunctionDefinitionExpression):
        local_variables = {function.parameters[i]: i for i in range(len(function.parameters))}
        def collect_local_variables(expression: Expression):
            if isinstance(expression, FunctionCallExpression):
                assert expression.name in self.functions, "UNKNOWN SYMBOL: {}".format(expression.token)
            elif isinstance(expression, VariableValueExpression):
                assert expression.name in local_variables, "UNKNOWN SYMBOL: {}".format(expression.token)
            elif isinstance(expression, VariableAssignmentExpression):
                local_variables[expression.name] = len(local_variables)
            return expression
        collect_local_variables(function)

        instructions = []
        address = self.text.put([])
        self.functions[function.name] = address

    def compile_expression(self, expression: Expression, variables: dict[str, ]):
        pass

    def compile_variable_value(self, expression: VariableValueExpression, variables: dict[str, ]):
        address = variables[expression.name]
        print("push [{}]".format(address))

    def compile_number_literal(self, expression: NumberLiteralExpression, variables: dict[str, ]):
        print("push [{}] ; number literal".format(expression.value))

    def compile_string_literal(self, expression: StringLiteralExpression, variables: dict[str, ]):
        address = self.data.put_string(expression.value)
        print("push [{}] ; string literal".format(address))

    def compile_variable_assignment(self, expression: VariableAssignmentExpression, variables: dict[str, ]):
        if expression.name not in variables:
            variables[expression.name] = "0x1"
        self.compile_expression(expression.value, variables)
        address = variables[expression.name]
        print("load [{}] ; variable assignment".format(address))

    def compile_binary_operator(self, expression: BinaryOperationExpression, variables: dict[str, ]):
        self.compile_expression(expression.first, variables)
        self.compile_expression(expression.second, variables)
        print("{} ; binary operator".format(expression.operator))
        print("swop")
        print("swop")


def ast_apply(root: Expression, modifier: Callable[[Expression], Expression]) -> None:
    root.apply(modifier)
    for node in root.children():
        ast_apply(node, modifier)

def check_scope(functions: set[str], variables: set[str], expression: Expression):
    def f(e: Expression) -> Expression:
        if isinstance(e, FunctionCallExpression):
            if e.name not in functions:
                print("UNDEFINED FUNCTION {}".format(e.token))
        elif isinstance(e, VariableValueExpression):
            if e.name not in variables:
                print("UNDEFINED VARIABLE {}".format(e.token))
        elif isinstance(e, VariableAssignmentExpression):
            variables.add(e.name)
        return e

    ast_apply(expression, f)

def check_declarations(global_root: RootExpression, functions_definitions: list[FunctionDefinitionExpression]):
    functions = set([function.name for function in functions_definitions])
    variables = set()
    for function in functions_definitions:
        check_scope(functions, set(function.parameters), function)
    check_scope(functions, variables, global_root)

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
    (print-str "Hello, world!")
    """)

    tokens = []
    while True:
        token = lex.next()
        if token is None:
            break
        # print(token)
        tokens.append(token)
    ast = Parser(tokens).parse()
    print(ast)

    funcs = []
    def extract_functions(expression: Expression) -> Expression:
        if type(expression) == FunctionDefinitionExpression:
            funcs.append(expression)
            return NumberLiteralExpression(expression.token, 0)
        return expression
    ast_apply(ast, extract_functions)
    check_declarations(ast, funcs)

if __name__ == '__main__':
    main()
    # ds = DataSegment(128)
    # print(ds.put_string("Hello, world!"))
    # print(ds.put_string("Hello, biba!"))
    # print(ds.layout())
