import contextlib
import io
import logging
import os
import tempfile
import unittest

import machine
import pytest
import translator
from lexer import Lexer
from parsing import Parser


@pytest.mark.golden_test("golden/*.yml")
def test_translator_and_machine(golden, caplog):
    """
    `poetry run pytest . -v --update-goldens`
    Вход:

    - `in_source` -- исходный код
    - `in_stdin` -- данные на ввод процессора для симуляции

    Выход:

    - `out_code` -- машинный код, сгенерированный транслятором
    - `out_stdout` -- стандартный вывод транслятора и симулятора
    - `out_log` -- журнал программы
    """
    # Установим уровень отладочного вывода на DEBUG
    caplog.set_level(logging.DEBUG)

    # Создаём временную папку для тестирования приложения.
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Готовим имена файлов для входных и выходных данных.
        source = os.path.join(tmpdirname, "source.bf")
        input_stream = os.path.join(tmpdirname, "input.txt")
        target = os.path.join(tmpdirname, "target.o")

        # Записываем входные данные в файлы. Данные берутся из теста.
        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])

        # Запускаем транслятор и собираем весь стандартный вывод в переменную
        # stdout
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target)
            print("============================================================")
            machine.main(target, input_stream)

        # Выходные данные также считываем в переменные.
        with open(target, encoding="utf-8") as file:
            code = file.read()

        # Проверяем, что ожидания соответствуют реальности.
        assert code == golden.out["out_code"]
        assert stdout.getvalue() == golden.out["out_stdout"]
        assert caplog.text == golden.out["out_log"]


class TestLexer(unittest.TestCase):
    def _assert_wrong(self, source: str):
        with pytest.raises(AssertionError):
            Lexer(source).tokenize()

    def test_unknown_tokens(self):
        unknown_symbols = "%$#@&№:"
        for symbol in unknown_symbols:
            self._assert_wrong(symbol)

    def test_wrong_char_literal(self):
        source = """
        'a"
        """
        self._assert_wrong(source)

    def test_wrong_string_literal(self):
        source = '"hello'
        self._assert_wrong(source)


class TestParser(unittest.TestCase):
    def _assert_wrong(self, source: str):
        with pytest.raises(AssertionError):
            Parser(Lexer(source).tokenize()).parse()

    def test_function_definition(self):
        self._assert_wrong("defun")
        self._assert_wrong("(defun")
        self._assert_wrong("defun)")
        self._assert_wrong("(defun)")
        self._assert_wrong("(defun()")
        self._assert_wrong("(defun))")

    def test_function_call(self):
        self._assert_wrong("(foo 1 2")
        self._assert_wrong("(2)")

    def test_allocation(self):
        self._assert_wrong("(alloc")
        self._assert_wrong("(alloc)")
        self._assert_wrong("(alloc str)")
        self._assert_wrong("(alloc (foo))")

    def test_binary(self):
        self._assert_wrong("(1 2")
        self._assert_wrong("(1 2)")
        self._assert_wrong("(+ 1 2")
        self._assert_wrong("(+ 1)")
        self._assert_wrong("(+)")
        self._assert_wrong("(+ 1 2 3)")

    def test_unary(self):
        self._assert_wrong("(not")
        self._assert_wrong("(not)")
        self._assert_wrong("(not 1 2)")

    def test_nullary(self):
        self._assert_wrong("(get")
        self._assert_wrong("(get 1)")
        self._assert_wrong("(get 1 2)")

    def test_loop(self):
        self._assert_wrong("(loop")
        self._assert_wrong("(loop)")

    def test_if_condition(self):
        self._assert_wrong("(if)")
        self._assert_wrong("if")
        self._assert_wrong("(if")
        self._assert_wrong("if)")
        self._assert_wrong("(if 1)")
        self._assert_wrong("(if 1 2)")
