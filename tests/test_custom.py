import cocotb
from random import randint

from helpers.tb_helper import start_clock, reset_dut
from helpers.memory import Memory
from helpers.matrix import gen_matrix
from helpers.tb_helper import run_config, run_load, run_gemm, run_store


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
    mem_length = 4096
    mem = Memory(mem_length)

    t = 5
    for _ in range(0, t):
        # Init
        m = randint(1, 16)
        n = randint(1, 16)
        p = randint(1, 16)

        A = gen_matrix(m, n)
        B = gen_matrix(n, p)

        mem.write_array(0x100, A)
        mem.write_array(0x200, B)

        await start_clock(dut)
        await reset_dut(dut)

        await run_config(dut, 0, 0x100, m, n)
        await run_config(dut, 1, 0x200, n, p)
        await run_config(dut, 2, 0x300, m, p)

        await run_load(dut, 0, mem.memory)
        await run_load(dut, 1, mem.memory)

        await run_gemm(dut, 0, 1, 2)

        await run_store(dut, 2, mem)

        dut_C = mem.read_array(0x300, m * p)
        golden_C = matmul(A, B, m, n, p)

        print("m, n, p =", m, n, p)
        print("A =", A)
        print("B =", B)
        print("DUT C =", dut_C)
        print("Golden C =", golden_C)

        assert dut_C == golden_C, f"Mismatch: DUT={dut_C}, GOLDEN={golden_C}"