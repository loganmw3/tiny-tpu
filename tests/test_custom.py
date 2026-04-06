import cocotb
from random import randint

from helpers.tb_helper import start_clock, reset_dut
from helpers.memory import memory_init, memory_read_array, memory_write_array
from helpers.matrix import gen_matrix
from helpers.tb_helper import run_config, run_load, run_gemm, run_store

# import cocotb
# from random import randint

# from helpers.tb_helper import start_clock, reset_dut
# from helpers.memory import memory_init, memory_read_array, memory_write_array
# from helpers.matrix import gen_matrix
# from helpers.tb_helper import run_config, run_load, run_gemm, run_store


def matmul(A, B, m, n, p):
    C = [0 for _ in range(m * p)]
    for i in range(m):
        for j in range(p):
            acc = 0
            for k in range(n):
                acc += A[i*n + k] * B[k*p + j]
            C[i*p + j] = acc & 0xFFFFFFFF
    return C


@cocotb.test()
async def test_custom(dut):
    memory = {}
    mem_length = 4096
    memory_init(memory, mem_length)

    # Init
    m = randint(1, 8)
    n = randint(1, 8)
    p = randint(1, 8)

    A = gen_matrix(m, n)
    B = gen_matrix(n, p)

    memory_write_array(memory, 0x100, A)
    memory_write_array(memory, 0x200, B)

    await start_clock(dut)
    await reset_dut(dut)

    await run_config(dut, 0, 0x100, m, n)
    await run_config(dut, 1, 0x200, n, p)
    await run_config(dut, 2, 0x300, m, p)

    await run_load(dut, 0, memory)
    await run_load(dut, 1, memory)

    await run_gemm(dut, 0, 1, 2)

    await run_store(dut, 2, memory)

    dut_C = memory_read_array(memory, 0x300, m * p)
    golden_C = matmul(A, B, m, n, p)

    print("m, n, p =", m, n, p)
    print("A =", A)
    print("B =", B)
    print("DUT C =", dut_C)
    print("Golden C =", golden_C)

    assert dut_C == golden_C, f"Mismatch: DUT={dut_C}, GOLDEN={golden_C}"