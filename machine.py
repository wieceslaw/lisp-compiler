from __future__ import annotations

import logging
import sys
from enum import Enum

from isa import Addressing, Opcode, Register
from translator import read_code

MAX_MEMORY_SIZE = 2**24
INT32_MAX = 2**31 - 1
INT32_MIN = -(2**31)
INT8_MAX = 2**7 - 1
INT8_MIN = -(2**7)
OPERAND_MAX = 2**23 - 1
OPERAND_MIN = -(2**23)
HALF_N = 2**32
N = HALF_N * 2


def overflow(value):
    return (value + HALF_N) % N - HALF_N


def is_valid_word(word: int) -> bool:
    return INT32_MAX >= word >= INT32_MIN


def is_valid_byte(byte: int) -> bool:
    return INT8_MAX >= byte >= INT8_MIN


def is_valid_address_word(word: int) -> bool:
    return OPERAND_MAX >= word >= OPERAND_MIN


def extract_address_value(address: dict):
    match address["type"]:
        case Addressing.RELATIVE:
            return address["offset"]
        case Addressing.RELATIVE_INDIRECT:
            return address["offset"]
        case Addressing.ABSOLUTE:
            return address["value"]
        case Addressing.CONTROL_FLOW:
            return address["value"]
        case _:
            assert False, "Unknown address type"


def register_selector(register: Register):
    match register:
        case Register.STACK_POINTER:
            return AluInSel.REG_SP
        case Register.FRAME_POINTER:
            return AluInSel.REG_FP
        case _:
            assert False, "Unknown register type"


class DataSelector(Enum):
    DATA_MEMORY = 0
    IO_PORT = 1


class AluInSel(Enum):
    ZERO = 0
    REG_AC = 1
    REG_FP = 2
    REG_BR = 3
    REG_SP = 4
    REG_IP = 5
    REG_DR = 6
    REG_AR = 7
    INS_OP = 8


class AluOutSel(Enum):
    REG_AC = 0
    REG_FP = 1
    REG_BR = 2
    REG_SP = 3
    REG_IP = 4
    REG_DR = 5
    REG_AR = 6


class AluOpSig(Enum):
    ADD = 0
    AND = 1
    OR = 2
    IS_NEG = 3
    IS_POS = 4
    IS_ZERO = 5


class ExecutionCycle(Enum):
    INSTRUCTION_FETCH = 0
    ADDRESS_FETCH = 1
    OPERAND_FETCH = 2
    EXECUTION = 3

    def next_cycle(self):
        match self:
            case ExecutionCycle.INSTRUCTION_FETCH:
                return ExecutionCycle.ADDRESS_FETCH
            case ExecutionCycle.ADDRESS_FETCH:
                return ExecutionCycle.OPERAND_FETCH
            case ExecutionCycle.OPERAND_FETCH:
                return ExecutionCycle.EXECUTION
            case ExecutionCycle.EXECUTION:
                return ExecutionCycle.INSTRUCTION_FETCH


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
        self._alu_in_left_selector = AluInSel.ZERO
        self._alu_in_right_selector = AluInSel.ZERO
        self._alu_out_selector = AluOutSel.REG_AC

        self._instruction_operand = 0

    def _port_read(self) -> int:
        if len(self._input_buffer) == 0:
            return 0  # EOF
        byte = self._input_buffer.pop(0)
        assert is_valid_byte(byte), "Out of byte bounds"
        return byte

    def _port_write(self, byte: int):
        assert is_valid_byte(byte), "Out of byte bounds"
        self._output_buffer.append(byte)

    def _clear_alu(self):
        self._alu_in_left_selector = 0
        self._alu_in_right_selector = 0
        self._alu_out_selector = 0
        self._instruction_operand = 0

    def _alu_operand(self, selector: AluInSel) -> int:
        match selector:
            case AluInSel.ZERO:
                return 0
            case AluInSel.REG_IP:
                return self._instruction_pointer
            case AluInSel.REG_AC:
                return self._accumulator
            case AluInSel.REG_AR:
                return self._address_register
            case AluInSel.REG_BR:
                return self._buffer_register
            case AluInSel.REG_DR:
                return self._data_register
            case AluInSel.REG_FP:
                return self._frame_pointer
            case AluInSel.REG_SP:
                return self._stack_pointer
            case AluInSel.INS_OP:
                return self._instruction_operand
            case _:
                assert False, "Unknown alu operand"

    def _alu_out(self, word: int):
        word = overflow(word)
        match self._alu_out_selector:
            case AluOutSel.REG_IP:
                self._instruction_pointer = word
            case AluOutSel.REG_AC:
                self._accumulator = word
            case AluOutSel.REG_AR:
                self._address_register = word
            case AluOutSel.REG_BR:
                self._buffer_register = word
            case AluOutSel.REG_DR:
                self._data_register = word
            case AluOutSel.REG_FP:
                self._frame_pointer = word
            case AluOutSel.REG_SP:
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
            assert self._address_register >= 0, "Invalid data address"
            self._memory[self._address_register] = self._data_register
        elif self._data_selector == DataSelector.IO_PORT:
            self._port_write(self._data_register)
        else:
            assert False, "Unknown data selector"

    def read_signal(self):
        if self._data_selector == DataSelector.DATA_MEMORY:
            assert self._address_register >= 0, "Invalid data address"
            self._data_register = self._memory[self._address_register]
        elif self._data_selector == DataSelector.IO_PORT:
            self._data_register = self._port_read()
        else:
            assert False, "Unknown data selector"

    def set_data_sel(self, selector: DataSelector):
        self._data_selector = selector

    def set_left_alu_in_sel(self, selector: AluInSel):
        self._alu_in_left_selector = selector

    def set_right_alu_in_sel(self, selector: AluInSel):
        assert selector != AluInSel.INS_OP, "Unknown selector"
        self._alu_in_right_selector = selector

    def set_alu_out_sel(self, selector: AluOutSel):
        self._alu_out_selector = selector

    def set_instruction_address_word(self, word: int):
        assert is_valid_address_word(word), "Value out of bounds"
        self._instruction_operand = word

    def alu_signal(
        self,
        operation: AluOpSig,
        invert_left: bool = False,
        invert_right: bool = False,
        increment: bool = False,
    ):
        left_operand = self._alu_operand(self._alu_in_left_selector)
        if invert_left:
            left_operand = ~left_operand
        right_operand = self._alu_operand(self._alu_in_right_selector)
        if invert_right:
            right_operand = ~right_operand
        match operation:
            case AluOpSig.ADD:
                value = left_operand + right_operand
            case AluOpSig.AND:
                value = left_operand & right_operand
            case AluOpSig.OR:
                value = left_operand | right_operand
            case AluOpSig.IS_NEG:
                value = int(left_operand < 0)
            case AluOpSig.IS_ZERO:
                value = int(left_operand == 0)
            case AluOpSig.IS_POS:
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
        self._execution_cycle = ExecutionCycle.INSTRUCTION_FETCH
        self._cycle_tick = 0

    def tick(self) -> bool:
        match self._execution_cycle:
            case ExecutionCycle.INSTRUCTION_FETCH:
                self._cycle_tick = self._instruction_fetch(self._cycle_tick)
            case ExecutionCycle.ADDRESS_FETCH:
                self._cycle_tick = self._address_fetch(self._cycle_tick)
            case ExecutionCycle.OPERAND_FETCH:
                self._cycle_tick = self._operand_fetch(self._cycle_tick)
            case ExecutionCycle.EXECUTION:
                self._cycle_tick = self._execute(self._cycle_tick)
        self._tick += 1
        if self._cycle_tick == -1:
            self._next_cycle()
        if self._execution_cycle == ExecutionCycle.INSTRUCTION_FETCH:
            return True  # begin of new cycle
        return False

    def current_tick(self):
        return self._tick

    def _next_cycle(self):
        self._cycle_tick = 0
        self._execution_cycle = self._execution_cycle.next_cycle()
        opcode = self._current_instruction()["opcode"]
        # skip address fetch
        if self._execution_cycle == ExecutionCycle.ADDRESS_FETCH and not opcode.is_address():
            self._execution_cycle = self._execution_cycle.next_cycle()
        # skip operand fetch
        if self._execution_cycle == ExecutionCycle.OPERAND_FETCH and not opcode.is_operand():
            self._execution_cycle = self._execution_cycle.next_cycle()

    def _instruction_address(self) -> int:
        return self._data_path.instruction_address()

    def _accumulator_zero(self) -> bool:
        return self._data_path.zero()

    def _current_instruction(self) -> dict:
        return self._command_register

    def _latch_command_register(self):
        assert self._instruction_address() >= 0, "Invalid instruction address"
        self._command_register = self._instruction_memory[self._instruction_address()]

    def _set_instruction_value(self):
        assert self._current_instruction()["opcode"].is_address()
        address = self._current_instruction()["address"]
        self._data_path.set_instruction_address_word(extract_address_value(address))

    def _alu_call(
        self,
        left_sel: AluInSel,
        right_sel: AluInSel,
        out_sel: AluOutSel,
        operation: AluOpSig,
        increment: bool = False,
        invert_left: bool = False,
        invert_right: bool = False,
    ):
        self._data_path.set_left_alu_in_sel(left_sel)
        self._data_path.set_right_alu_in_sel(right_sel)
        self._data_path.set_alu_out_sel(out_sel)
        self._data_path.alu_signal(operation, increment=increment, invert_left=invert_left, invert_right=invert_right)

    def _alu_move(self, src: AluInSel, dst: AluOutSel):
        self._alu_call(src, AluInSel.ZERO, dst, AluOpSig.ADD)

    def _instruction_fetch(self, tick: int) -> int:
        match tick:
            case 0:
                assert self._instruction_address() >= 0, "Invalid instruction address"
                self._latch_command_register()
                self._data_path.set_left_alu_in_sel(AluInSel.REG_IP)
                self._data_path.set_right_alu_in_sel(AluInSel.ZERO)
                self._data_path.set_alu_out_sel(AluOutSel.REG_IP)
                self._data_path.alu_signal(AluOpSig.ADD, increment=True)
                return -1
            case _:
                assert False, "Unexpected tick {}".format(tick)

    def _address_fetch(self, tick: int) -> int:
        self._set_instruction_value()
        address = self._current_instruction()["address"]
        operand_type = address["type"]
        match operand_type:
            case Addressing.ABSOLUTE:
                match tick:
                    case 0:
                        self._alu_move(AluInSel.INS_OP, AluOutSel.REG_AR)
                        return -1
            case Addressing.CONTROL_FLOW:
                match tick:
                    case 0:
                        self._alu_move(AluInSel.INS_OP, AluOutSel.REG_DR)
                        return -1
            case Addressing.RELATIVE:
                match tick:
                    case 0:
                        register = address["register"]
                        selector = register_selector(register)
                        self._alu_call(AluInSel.INS_OP, selector, AluOutSel.REG_AR, AluOpSig.ADD)
                        return -1
            case Addressing.RELATIVE_INDIRECT:
                match tick:
                    case 0:
                        register = address["register"]
                        selector = register_selector(register)
                        self._alu_call(AluInSel.INS_OP, selector, AluOutSel.REG_AR, AluOpSig.ADD)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                        self._data_path.read_signal()
                        return tick + 1
                    case 2:
                        self._alu_move(AluInSel.REG_DR, AluOutSel.REG_AR)
                        return -1
        assert False, "Unexpected tick or address type {} {}".format(tick, address)

    def _operand_fetch(self, tick: int) -> int:
        match tick:
            case 0:
                self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                self._data_path.read_signal()
                return -1
        assert False, "Unexpected tick {}".format(tick)

    def _execute(self, tick: int) -> int:
        # TODO: refactor
        opcode = self._current_instruction()["opcode"]
        match opcode:
            case Opcode.ADD:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.REG_DR, AluOutSel.REG_AC, AluOpSig.ADD)
                        return -1
            case Opcode.SUB:
                match tick:
                    case 0:
                        self._alu_call(
                            AluInSel.REG_AC,
                            AluInSel.REG_DR,
                            AluOutSel.REG_AC,
                            AluOpSig.ADD,
                            increment=True,
                            invert_right=True,
                        )
                        return -1
            case Opcode.AND:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.REG_DR, AluOutSel.REG_AC, AluOpSig.AND)
                        return -1
            case Opcode.OR:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.REG_DR, AluOutSel.REG_AC, AluOpSig.OR)
                        return -1
            case Opcode.NOT:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.ZERO, AluOutSel.REG_AC, AluOpSig.ADD, invert_left=True)
                        return -1
            case Opcode.JMP:
                match tick:
                    case 0:
                        self._alu_move(AluInSel.REG_DR, AluOutSel.REG_IP)
                        return -1
            case Opcode.JZ:
                match tick:
                    case 0:
                        if self._accumulator_zero():
                            self._alu_move(AluInSel.REG_DR, AluOutSel.REG_IP)
                        return -1
            case Opcode.PUSH:
                match tick:
                    case 0:
                        self._alu_call(
                            AluInSel.REG_SP, AluInSel.ZERO, AluOutSel.REG_SP, AluOpSig.ADD, invert_right=True
                        )
                        return -1
            case Opcode.POP:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_SP, AluInSel.ZERO, AluOutSel.REG_SP, AluOpSig.ADD, increment=True)
                        return -1
            case Opcode.IS_POS:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.ZERO, AluOutSel.REG_AC, AluOpSig.IS_POS)
                        return -1
            case Opcode.IS_NEG:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.ZERO, AluOutSel.REG_AC, AluOpSig.IS_NEG)
                        return -1
            case Opcode.IS_ZERO:
                match tick:
                    case 0:
                        self._alu_call(AluInSel.REG_AC, AluInSel.ZERO, AluOutSel.REG_AC, AluOpSig.IS_ZERO)
                        return -1
            case Opcode.PUT:
                match tick:
                    case 0:
                        self._alu_move(AluInSel.REG_AC, AluOutSel.REG_DR)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_sel(DataSelector.IO_PORT)
                        self._data_path.write_signal()
                        return -1
            case Opcode.GET:
                match tick:
                    case 0:
                        self._data_path.set_data_sel(DataSelector.IO_PORT)
                        self._data_path.read_signal()
                        return tick + 1
                    case 1:
                        self._alu_move(AluInSel.REG_DR, AluOutSel.REG_AC)
                        return -1
            case Opcode.ST:
                match tick:
                    case 0:
                        self._alu_move(AluInSel.REG_AC, AluOutSel.REG_DR)
                        return tick + 1
                    case 1:
                        self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                        self._data_path.write_signal()
                        return -1
            case Opcode.LD:
                match tick:
                    case 0:
                        self._alu_move(AluInSel.REG_DR, AluOutSel.REG_AC)
                        return -1
            case Opcode.CALL:
                return self._execute_call(tick)
            case Opcode.RET:
                return self._execute_ret(tick)
            case Opcode.NOP:
                return -1
            case Opcode.HALT:
                raise StopIteration()
        assert False, "Unknown opcode or tick {} {}".format(opcode, tick)

    def _execute_call(self, tick: int) -> int:
        match tick:
            case 0:
                self._alu_move(AluInSel.REG_DR, AluOutSel.REG_BR)
                return tick + 1
            case 1:
                self._alu_move(AluInSel.REG_IP, AluOutSel.REG_DR)
                return tick + 1
            case 2:
                self._alu_move(AluInSel.REG_SP, AluOutSel.REG_AR)
                return tick + 1
            case 3:
                self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                self._data_path.write_signal()
                return tick + 1
            case 4:
                self._alu_call(AluInSel.REG_SP, AluInSel.ZERO, AluOutSel.REG_SP, AluOpSig.ADD, invert_right=True)
                return tick + 1
            case 5:
                self._alu_move(AluInSel.REG_FP, AluOutSel.REG_DR)
                return tick + 1
            case 6:
                self._alu_move(AluInSel.REG_SP, AluOutSel.REG_AR)
                return tick + 1
            case 7:
                self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                self._data_path.write_signal()
                return tick + 1
            case 8:
                self._alu_call(AluInSel.REG_SP, AluInSel.ZERO, AluOutSel.REG_SP, AluOpSig.ADD, invert_right=True)
                return tick + 1
            case 9:
                self._alu_move(AluInSel.REG_SP, AluOutSel.REG_FP)
                return tick + 1
            case 10:
                self._alu_move(AluInSel.REG_BR, AluOutSel.REG_IP)
                return -1
        assert False, "Unexpected tick {}".format(tick)

    def _execute_ret(self, tick: int) -> int:
        match tick:
            case 0:
                self._alu_call(AluInSel.REG_SP, AluInSel.ZERO, AluOutSel.REG_SP, AluOpSig.ADD, increment=True)
                return tick + 1
            case 1:
                self._alu_move(AluInSel.REG_SP, AluOutSel.REG_AR)
                return tick + 1
            case 2:
                self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                self._data_path.read_signal()
                return tick + 1
            case 3:
                self._alu_move(AluInSel.REG_DR, AluOutSel.REG_FP)
                return tick + 1
            case 4:
                self._alu_call(AluInSel.REG_SP, AluInSel.ZERO, AluOutSel.REG_SP, AluOpSig.ADD, increment=True)
                return tick + 1
            case 5:
                self._alu_move(AluInSel.REG_SP, AluOutSel.REG_AR)
            case 6:
                self._data_path.set_data_sel(DataSelector.DATA_MEMORY)
                self._data_path.read_signal()
                return tick + 1
            case 7:
                self._alu_move(AluInSel.REG_DR, AluOutSel.REG_IP)
                return -1
        assert False, "Unexpected tick {}".format(tick)

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
    data_path = DataPath(data_memory_size, data_segment, input_tokens)
    control_unit = ControlUnit(instruction_memory_size, text_segment, data_path)
    logging.debug("%s", control_unit)
    instruction_count = 0
    try:
        while control_unit.current_tick() < limit:
            if control_unit.tick():
                instruction_count += 1
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass
    logging.info("output_buffer: %s", data_path.get_output_buffer())
    output = "".join([chr(byte) for byte in data_path.get_output_buffer()])
    return output, instruction_count, control_unit.current_tick()


def main(code_file: str, input_file: str):
    text_segment, data_segment = read_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_tokens = []
        for char in input_text:
            input_tokens.append(ord(char))

    output, instruction_count, ticks = simulation(
        data_segment,
        text_segment,
        data_memory_size=2048,
        instruction_memory_size=2048,
        input_tokens=input_tokens,
        limit=10000000,
    )

    print("".join(output))
    print("instruction count: {} ticks: {}".format(instruction_count, ticks))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
