MAX_MEMORY_SIZE = 2 ** 24


class DataPath:
    def __init__(self, memory_size: int, data_segment, input_buffer):
        assert memory_size <= MAX_MEMORY_SIZE, "Memory address limit exceeded"
        assert memory_size >= len(data_segment), \
            "Not enough memory to initialize memory, have: {}, need: {}".format(memory_size, len(data_segment))
        self.memory_size = memory_size
        self.memory = [0] * memory_size
        # copy data to memory
        for i, word in enumerate(data_segment):
            self.memory[i] = word
        self.input_buffer = input_buffer

