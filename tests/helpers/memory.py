class Memory:
    def __init__(self, size: int):
        self.memory = {}
        self.mem_init(size)

    def mem_init(self, size: int):
        for i in range(size):
            self.memory[i] = 0 & 0xFFFFFFFF

    def read_val(self, addr: int):
        return self.memory[addr]

    def write_val(self, addr: int, val: int):
        self.memory[addr] = val & 0xFFFFFFFF

    def write_array(self, addr: int, vals: list[int]):
        for i, val in enumerate(vals):
            self.write_val(addr + i, val)

    def read_array(self, addr: int, n: int):
        result = []
        for i in range(n):
            result.append(self.read_val(addr + i))
        return result