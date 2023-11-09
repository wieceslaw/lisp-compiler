from translator import *


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
    pass


class Compiler:
    def __init__(self):
        self.text = None
        self.data = None
        self.functions = []

class Traverser:
    def __init__(self, functions: dict) -> None:
        self.functions = functions

    def traverse_expression(self, expression: Expression) -> None:
        if isinstance(expression, FunctionCallExpression):
            self.traverse_function_call_expression(expression)
        elif isinstance(expression, FunctionDefinitionExpression):
            self.traverse_function_definition_expression(expression)
        elif isinstance(expression, LoopExpression):
            pass
        elif isinstance(expression, ConditionExpression):
            pass
        elif isinstance(expression, StringLiteralExpression):
            pass
        elif isinstance(expression, NumberLiteralExpression):
            pass
        elif isinstance(expression, VariableValueExpression):
            pass
        elif isinstance(expression, VariableAssignmentExpression):
            pass
        elif isinstance(expression, BinaryOperationExpression):
            pass
        else:
            assert False, "Unknown expression"

    def traverse_expressions(self, expressions: list[Expression]) -> None:
        for expression in expressions:
            self.traverse_expression(expression)

    def traverse_function_call_expression(self, expression: FunctionCallExpression) -> None:
        self.functions[FunctionCallExpression](expression)

    def traverse_function_definition_expression(self, expression: FunctionDefinitionExpression) -> None:
        pass


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

    # alloc directive
    # defvar directive?
    tokens = []
    while True:
        token = lex.next()
        if token is None:
            break
        # print(token)
        tokens.append(token)
    ast = Parser(tokens).parse_expressions()
    print(ast)
    Traverser([

    ]).traverse_expressions(ast)

if __name__ == '__main__':
    main()
    # ds = DataSegment(128)
    # print(ds.put_string("Hello, world!"))
    # print(ds.put_string("Hello, biba!"))
    # print(ds.layout())
