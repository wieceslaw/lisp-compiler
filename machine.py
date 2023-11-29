class DataPath:
    def __init__(self, memory_size, data_segment, input_buffer):
        assert memory_size >= len(data_segment), "Not enough memory to load data"
        self.memory_size = memory_size
        self.memory = [0] * memory_size
        # copy data to memory
        for i, word in enumerate(data_segment):
            self.memory[i] = word
        self.input_buffer = input_buffer
