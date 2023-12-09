from __future__ import annotations

import logging
import sys
from enum import Enum

from isa import Addressing, Opcode, Register
from translator import read_code

MAX_MEMORY_SIZE = 2**24
INT32_MAX = 2**32 - 1
INT32_MIN = -(2**32)
INT8_MAX = 2**8 - 1
INT8_MIN = -(2**8)
OPERAND_MAX = 2**24 - 1
OPERAND_MIN = 0


def is_valid_word(word: int) -> bool:
    return INT32_MAX >= word >= INT32_MIN


def is_valid_byte(byte: int) -> bool:
    return INT8_MAX >= byte >= INT8_MIN


def is_valid_operand(operand: int) -> bool:
    return OPERAND_MAX >= operand >= OPERAND_MIN


def extract_operand_value(operand: dict):
    match operand["type"]:
        case Addressing.RELATIVE:
            return operand["offset"]
        case Addressing.RELATIVE_INDIRECT:
            return operand["offset"]
        case Addressing.ABSOLUTE:
            return operand["address"]
        case Addressing.CONTROL_FLOW:
            return operand["address"]
        case _:
            assert False, "Unknown address type"


def register_selector(register: Register):
    match register:
        case Register.STACK_POINTER:
            return AluInSelector.REG_SP
        case Register.FRAME_POINTER:
            return AluInSelector.REG_FP
        case _:
            assert False, "Unknown register type"


class DataSelector(Enum):
    DATA_MEMORY = 0
    IO_PORT = 1


class AluInSelector(Enum):
    ZERO = 0
    REG_AC = 1
    REG_FP = 2
    REG_BR = 3
    REG_SP = 4
    REG_IP = 5
    REG_DR = 6
    REG_AR = 7
    INS_OP = 8


class AluOutSelector(Enum):
    REG_AC = 0
    REG_FP = 1
    REG_BR = 2
    REG_SP = 3
    REG_IP = 4
    REG_DR = 5
    REG_AR = 6


class AluOperationSignal(Enum):
    ADD = 0
    AND = 1
    OR = 2
    IS_NEG = 3
    IS_POS = 4
    IS_ZERO = 5


class DataPath:
    def __init__(self, data_memory_size: int, data_segment: list[int], input_buffer: list[int]):
        assert data_memory_size <= MAX_MEMORY_SIZE, "Out of memory bounds"
        assert data_memory_size >= len(
            data_segment
        ), "Not enough memory to initialize memory, have: {}, need: {}".format(data_memory_size, len(data_segment))
        self._memory_size = data_memory_size
        self._memory = [0] * data_memory_size
        # copy data to memory
        for i, word in enumerate(data_segment):
            self._memory[i] = word
        self._input_buffer = input_buffer
        self._output_buffer = []

        # register file
        self._accumulator = 0
        self._frame_pointer = 0
        self._buffer_register = 0
        self._stack_pointer = data_memory_size - 1
        self._instruction_pointer = 0
        self._data_register = 0
        self._address_register = 0

        # selectors
        self._data_selector = DataSelector.DATA_MEMORY
        self._alu_in_left_selector = AluInSelector.ZERO
        self._alu_in_right_selector = AluInSelector.ZERO
        self._alu_out_selector = AluOutSelector.REG_AC

        self._instruction_operand = 0

    def _port_read(self) -> int:
        return self._input_buffer.pop(0)

    def _port_write(self, word: int):
        assert is_valid_byte(word), "Out of byte bounds"
        self._output_buffer.append(word)

    def _clear_alu(self):
        self._alu_in_left_selector = 0
        self._alu_in_right_selector = 0
        self._alu_out_selector = 0
        self._instruction_operand = 0

    def _alu_operand(self, selector: AluInSelector) -> int:
        match selector:
            case AluInSelector.ZERO:
                return 0
            case AluInSelector.REG_IP:
                return self._instruction_pointer
            case AluInSelector.REG_AC:
                return self._accumulator
            case AluInSelector.REG_AR:
                return self._address_register
            case AluInSelector.REG_BR:
                return self._buffer_register
            case AluInSelector.REG_DR:
                return self._data_register
            case AluInSelector.REG_FP:
                return self._frame_pointer
            case AluInSelector.REG_SP:
                return self._stack_pointer
            case AluInSelector.INS_OP:
                return self._instruction_operand
            case _:
                assert False, "Unknown alu operand"

    def _alu_out(self, word: int):
        match self._alu_out_selector:
            case AluOutSelector.REG_IP:
                self._instruction_pointer = word
            case AluOutSelector.REG_AC:
                self._accumulator = word
            case AluOutSelector.REG_AR:
                self._address_register = word
            case AluOutSelector.REG_BR:
                self._buffer_register = word
            case AluOutSelector.REG_DR:
                self._data_register = word
            case AluOutSelector.REG_FP:
                self._frame_pointer = word
            case AluOutSelector.REG_SP:
                self._stack_pointer = word
            case _:
                assert False, "Unknown alu output"

    def zero(self) -> bool:
        return self._accumulator == 0

    def instruction_address(self) -> int:
        return self._instruction_pointer

    def get_output_buffer(self) -> list[int]:
        return self._output_buffer

    def write_signal(self):
        if self._data_selector == DataSelector.DATA_MEMORY:
            self._memory[self._address_register] = self._data_register
        elif self._data_selector == DataSelector.IO_PORT:
            self._port_write(self._data_register)
        else:
            assert False, "Unknown data selector"

    def read_signal(self):
        if self._data_selector == DataSelector.DATA_MEMORY:
            self._data_register = self._memory[self._address_register]
        elif self._data_selector == DataSelector.IO_PORT:
            self._data_register = self._port_read()
        else:
            assert False, "Unknown data selector"

    def set_data_select(self, selector: DataSelector):
        self._data_selector = selector

    def set_left_alu_in_selector(self, selector: AluInSelector):
        self._alu_in_left_selector = selector

    def set_right_alu_in_selector(self, selector: AluInSelector):
        assert selector != AluInSelector.INS_OP, "Unknown selector"
        self._alu_in_right_selector = selector

    def set_alu_out_selector(self, selector: AluOutSelector):
        self._alu_out_selector = selector

    def set_instruction_operand(self, operand: int):
        # assert is_valid_operand(operand), "Operand value out of bounds"
        self._instruction_operand = operand

    def alu_signals(
        self,
        operation: AluOperationSignal,
        left_invert: bool = False,
        right_invert: bool = False,
        increment: bool = False,
    ):
        left_operand = self._alu_operand(self._alu_in_left_selector)
        if left_invert:
            left_operand = ~left_operand
        right_operand = self._alu_operand(self._alu_in_right_selector)
        if right_invert:
            right_operand = ~right_operand
        match operation:
            case AluOperationSignal.ADD:
                value = left_operand + right_operand
            case AluOperationSignal.AND:
                value = left_operand & right_operand
            case AluOperationSignal.OR:
                value = left_operand | right_operand
            case AluOperationSignal.IS_NEG:
                value = int(left_operand < 0)
            case AluOperationSignal.IS_ZERO:
                value = int(left_operand == 0)
            case AluOperationSignal.IS_POS:
                value = int(left_operand > 0)
            case _:
                assert False, "Unknown signal"
        if increment:
            value += 1
        self._alu_out(value)
        self._clear_alu()

    def __repr__(self):
        return "REGISTERS: [AC:{} FP:{} BR:{} SP:{} IP:{} DR:{} AR:{}]".format(
            self._accumulator,
            self._frame_pointer,
            self._buffer_register,
            self._stack_pointer,
            self._instruction_pointer,
            self._data_register,
            self._address_register,
        )


class ControlUnit:
    def __init__(self, instruction_memory_size: int, program: list[dict], data_path: DataPath):
        assert instruction_memory_size <= MAX_MEMORY_SIZE, "Out of memory bounds"
        assert len(program) < instruction_memory_size, "Not enough instruction memory for program"
        self._instruction_memory = program
        self._data_path = data_path
        self._tick = 0
        self._command_register = None

    def _instruction_address(self) -> int:
        return self._data_path.instruction_address()

    def _accumulator_zero(self) -> bool:
        return self._data_path.zero()

    def _current_instruction(self) -> dict:
        return self._command_register

    def _latch_command_register(self):
        self._command_register = self._instruction_memory[self._instruction_address()]

    def _set_instruction_operand(self):
        assert "operand" in self._command_register, "Is not an address command [{}]".format(self._command_register)
        operand = self._command_register["operand"]
        self._data_path.set_instruction_operand(extract_operand_value(operand))

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def decode_and_execute_instruction(self):
        instruction_fetch_tick = 0
        while instruction_fetch_tick != -1:
            instruction_fetch_tick = self._instruction_fetch(instruction_fetch_tick)
            self.tick()

        operand_fetch_tick = 0
        while operand_fetch_tick != -1:
            operand_fetch_tick = self._operand_fetch(operand_fetch_tick)
            self.tick()

        execution_tick = 0
        while execution_tick != -1:
            execution_tick = self._execute(execution_tick)
            self.tick()

    def _instruction_fetch(self, tick: int) -> int:
        match tick:
            case 0:
                self._command_register = self._instruction_memory[self._instruction_address()]
                self._data_path.set_left_alu_in_selector(AluInSelector.REG_IP)
                self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                self._data_path.set_alu_out_selector(AluOutSelector.REG_IP)
                self._data_path.alu_signals(AluOperationSignal.ADD, increment=True)
                return -1
            case _:
                assert False, "Unexpected tick {}".format(tick)

    def _operand_fetch(self, tick: int) -> int:
        operand = self._current_instruction().get("operand")
        if operand is None:
            return -1
        self._set_instruction_operand()
        operand_type = operand["type"]
        match operand_type:
            case Addressing.ABSOLUTE:
                match tick:
                    case 0:
                        self._move(AluInSelector.INS_OP, AluOutSelector.REG_AR)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                        self._data_path.read_signal()
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)

            case Addressing.CONTROL_FLOW:
                match tick:
                    case 0:
                        self._move(AluInSelector.INS_OP, AluOutSelector.REG_DR)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)

            case Addressing.RELATIVE:
                match tick:
                    case 0:
                        register = operand["register"]
                        selector = register_selector(register)
                        self._data_path.set_left_alu_in_selector(AluInSelector.INS_OP)
                        self._data_path.set_right_alu_in_selector(selector)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AR)
                        self._data_path.alu_signals(AluOperationSignal.ADD)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                        self._data_path.read_signal()
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)

            case Addressing.RELATIVE_INDIRECT:
                match tick:
                    case 0:
                        register = operand["register"]
                        selector = register_selector(register)
                        self._data_path.set_left_alu_in_selector(AluInSelector.INS_OP)
                        self._data_path.set_right_alu_in_selector(selector)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AR)
                        self._data_path.alu_signals(AluOperationSignal.ADD)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                        self._data_path.read_signal()
                        return tick + 1
                    case 2:
                        self._move(AluInSelector.REG_DR, AluOutSelector.REG_AR)
                        return tick + 1
                    case 3:
                        self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                        self._data_path.read_signal()
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)

            case _:
                assert False, "Unknown operand type {}".format(operand_type)

    def _execute(self, tick: int) -> int:
        opcode = self._current_instruction()["opcode"]
        match opcode:
            case Opcode.ADD:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.REG_DR)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.ADD)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.SUB:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.REG_DR)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.ADD, increment=True, right_invert=True)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.AND:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.REG_DR)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.AND)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.OR:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.REG_DR)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.OR)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.NOT:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.ADD, left_invert=True)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.JMP:
                match tick:
                    case 0:
                        self._move(AluInSelector.REG_DR, AluOutSelector.REG_IP)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.JZ:
                match tick:
                    case 0:
                        if self._accumulator_zero():
                            self._move(AluInSelector.REG_DR, AluOutSelector.REG_IP)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.PUSH:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_SP)
                        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_SP)
                        self._data_path.alu_signals(AluOperationSignal.ADD, right_invert=True)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.POP:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_SP)
                        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_SP)
                        self._data_path.alu_signals(AluOperationSignal.ADD, increment=True)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.IS_POS:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.IS_POS)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.IS_NEG:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.IS_NEG)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.IS_ZERO:
                match tick:
                    case 0:
                        self._data_path.set_left_alu_in_selector(AluInSelector.REG_AC)
                        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                        self._data_path.set_alu_out_selector(AluOutSelector.REG_AC)
                        self._data_path.alu_signals(AluOperationSignal.IS_ZERO)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.PUT:
                match tick:
                    case 0:
                        self._move(AluInSelector.REG_AC, AluOutSelector.REG_DR)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_select(DataSelector.IO_PORT)
                        self._data_path.write_signal()
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.GET:
                match tick:
                    case 0:
                        self._data_path.set_data_select(DataSelector.IO_PORT)
                        self._data_path.read_signal()
                        return tick + 1
                    case 1:
                        self._move(AluInSelector.REG_DR, AluOutSelector.REG_AC)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.ST:
                match tick:
                    case 0:
                        self._move(AluInSelector.REG_AC, AluOutSelector.REG_DR)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                        self._data_path.write_signal()
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.LD:
                match tick:
                    case 0:
                        self._move(AluInSelector.REG_DR, AluOutSelector.REG_AC)
                        return -1
                    case _:
                        assert False, "Unexpected tick {}".format(tick)
            case Opcode.CALL:
                return self._execute_call(tick)
            case Opcode.RET:
                return self._execute_ret(tick)
            case Opcode.NOP:
                return -1
            case Opcode.HALT:
                raise StopIteration()
            case _:
                assert False, "Unknown opcode {}".format(opcode)

    def _execute_call(self, tick: int) -> int:
        match tick:
            case 0:
                self._move(AluInSelector.REG_DR, AluOutSelector.REG_BR)
                return tick + 1
            case 1:
                self._move(AluInSelector.REG_IP, AluOutSelector.REG_DR)
                return tick + 1
            case 2:
                self._move(AluInSelector.REG_SP, AluOutSelector.REG_AR)
                return tick + 1
            case 3:
                self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                self._data_path.write_signal()
                return tick + 1
            case 4:
                self._data_path.set_left_alu_in_selector(AluInSelector.REG_SP)
                self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                self._data_path.set_alu_out_selector(AluOutSelector.REG_SP)
                self._data_path.alu_signals(AluOperationSignal.ADD, right_invert=True)
                return tick + 1
            case 5:
                self._move(AluInSelector.REG_FP, AluOutSelector.REG_DR)
                return tick + 1
            case 6:
                self._move(AluInSelector.REG_SP, AluOutSelector.REG_AR)
                return tick + 1
            case 7:
                self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                self._data_path.write_signal()
                return tick + 1
            case 8:
                self._data_path.set_left_alu_in_selector(AluInSelector.REG_SP)
                self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                self._data_path.set_alu_out_selector(AluOutSelector.REG_SP)
                self._data_path.alu_signals(AluOperationSignal.ADD, right_invert=True)
                return tick + 1
            case 9:
                self._move(AluInSelector.REG_SP, AluOutSelector.REG_FP)
                return tick + 1
            case 10:
                self._move(AluInSelector.REG_BR, AluOutSelector.REG_IP)
                return -1
            case _:
                assert False, "Unexpected tick {}".format(tick)

    def _execute_ret(self, tick: int) -> int:
        match tick:
            case 0:
                self._data_path.set_left_alu_in_selector(AluInSelector.REG_SP)
                self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                self._data_path.set_alu_out_selector(AluOutSelector.REG_SP)
                self._data_path.alu_signals(AluOperationSignal.ADD, increment=True)
                return tick + 1
            case 1:
                self._move(AluInSelector.REG_SP, AluOutSelector.REG_AR)
                return tick + 1
            case 2:
                self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                self._data_path.read_signal()
                return tick + 1
            case 3:
                self._move(AluInSelector.REG_DR, AluOutSelector.REG_FP)
                return tick + 1
            case 4:
                self._data_path.set_left_alu_in_selector(AluInSelector.REG_SP)
                self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
                self._data_path.set_alu_out_selector(AluOutSelector.REG_SP)
                self._data_path.alu_signals(AluOperationSignal.ADD, increment=True)
                return tick + 1
            case 5:
                self._move(AluInSelector.REG_SP, AluOutSelector.REG_AR)
                return tick + 1
            case 6:
                self._data_path.set_data_select(DataSelector.DATA_MEMORY)
                self._data_path.read_signal()
                return tick + 1
            case 7:
                self._move(AluInSelector.REG_DR, AluOutSelector.REG_IP)
                return -1
            case _:
                assert False, "Unexpected tick {}".format(tick)

    def _move(self, src: AluInSelector, dst: AluOutSelector):
        self._data_path.set_left_alu_in_selector(src)
        self._data_path.set_right_alu_in_selector(AluInSelector.ZERO)
        self._data_path.set_alu_out_selector(dst)
        self._data_path.alu_signals(AluOperationSignal.ADD)

    def __repr__(self):
        return "TICK: {:3} CR: {} DATA PATH: {}".format(self._tick, self._current_instruction(), self._data_path)


def simulation(
    data_segment: list[int],
    text_segment: list[dict],
    data_memory_size: int,
    instruction_memory_size: int,
    input_tokens: list[int],
    limit: int,
):
    data_path = DataPath(data_memory_size, data_segment, [*input_tokens, 0])
    control_unit = ControlUnit(instruction_memory_size, text_segment, data_path)
    instr_counter = 0

    logging.debug("%s", control_unit)
    try:
        while instr_counter < limit:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", data_path.get_output_buffer())
    output = "".join([chr(byte) for byte in data_path.get_output_buffer()])
    return output, instr_counter, control_unit.current_tick()


def main(code_file: str, input_file: str):
    text_segment, data_segment = read_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_tokens = []
        for char in input_text:
            input_tokens.append(ord(char))

    output, instr_counter, ticks = simulation(
        data_segment,
        text_segment,
        data_memory_size=2048,
        instruction_memory_size=2048,
        input_tokens=input_tokens,
        limit=10000000,
    )

    print("".join(output))
    print("instr_counter: {}, ticks: {}".format(instr_counter, ticks))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
