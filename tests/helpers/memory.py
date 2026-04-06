def memory_init(memory, size: int):
    for i in range(size):
        memory[i] = 0 & 0xFFFFFFFF
    return
        
        
def memory_read(memory, addr: int):
    return memory[addr]


def memory_write(memory, addr: int, val: int):
    write_val = val & 0xFFFFFFFF
    memory[addr] = write_val
    return


def memory_write_array(memory, addr: int, vals: list[int]):
    for i, val in enumerate(vals):
        memory_write(memory, addr+i, val)
    return


def memory_read_array(memory, addr: int, n: int):
    result = []
    for i in range(n):
        result.append(memory_read(memory, addr+i))
    return result