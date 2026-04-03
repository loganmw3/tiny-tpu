import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

OPCODE_CONFIG = 0b10001
OPCODE_LOAD   = 0b00111
OPCODE_STORE  = 0b00110
OPCODE_GEMM   = 0b11111


def encode_config(target_spad: int, ptr: int, rows: int, cols: int) -> int:
    return (
        (OPCODE_CONFIG << 59)
        | ((target_spad & 0x7) << 56)
        | ((ptr & 0xFFFFFFFF) << 16)
        | ((rows & 0xFF) << 8)
        | (cols & 0xFF)
    )


def encode_load(target_spad: int) -> int:
    return (
        (OPCODE_LOAD << 59)
        | ((target_spad & 0x7) << 56)
    )


def encode_store(target_spad: int) -> int:
    return (
        (OPCODE_STORE << 59)
        | ((target_spad & 0x7) << 56)
    )


def encode_gemm(spad_a: int, spad_b: int, spad_c: int) -> int:
    return (
        (OPCODE_GEMM << 59)
        | ((spad_a & 0x7) << 56)
        | ((spad_b & 0x7) << 53)
        | ((spad_c & 0x7) << 50)
    )


async def wait_for_commit(dut, timeout=300):
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.commit_en.value) == 1:
            return
    assert False, "Timeout waiting for commit"


async def run_config(dut, target_spad: int, ptr: int, rows: int, cols: int):
    dut.instruction.value = encode_config(target_spad, ptr, rows, cols)
    await wait_for_commit(dut)
    await RisingEdge(dut.clk)
    dut.instruction.value = 0
    await RisingEdge(dut.clk)


async def run_load(dut, target_spad: int, memory: dict[int, int], timeout=1200):
    dut.instruction.value = encode_load(target_spad)

    for _ in range(timeout):
        await RisingEdge(dut.clk)

        if int(dut.mem_ren.value) == 1:
            addr = int(dut.mem_raddr.value)
            dut.mem_rdata.value = memory.get(addr, 0)
            dut.mem_rvalid.value = 1
        else:
            dut.mem_rvalid.value = 0

        if int(dut.commit_en.value) == 1:
            break
    else:
        assert False, f"Timeout waiting for LOAD on spad {target_spad}"

    dut.mem_rvalid.value = 0
    dut.mem_rdata.value = 0
    dut.instruction.value = 0
    await RisingEdge(dut.clk)


async def run_gemm(dut, spad_a: int, spad_b: int, spad_c: int, timeout=2500):
    dut.instruction.value = encode_gemm(spad_a, spad_b, spad_c)

    for cyc in range(timeout):
        await RisingEdge(dut.clk)
        await ReadOnly()

        if int(dut.commit_en.value) == 1:
            break
    else:
        assert False, f"Timeout waiting for GEMM {spad_a} x {spad_b} -> {spad_c}"

    await RisingEdge(dut.clk)
    dut.instruction.value = 0
    await RisingEdge(dut.clk)


async def run_store(dut, target_spad: int, written_memory: dict[int, int], timeout=1500):
    dut.instruction.value = encode_store(target_spad)

    for _ in range(timeout):
        await RisingEdge(dut.clk)
        await ReadOnly()

        if int(dut.mem_wen.value) == 1:
            addr = int(dut.mem_waddr.value)
            data = int(dut.mem_wdata.value)
            written_memory[addr] = data

        if int(dut.commit_en.value) == 1:
            break
    else:
        assert False, f"Timeout waiting for STORE on spad {target_spad}"

    await RisingEdge(dut.clk)
    dut.instruction.value = 0
    await RisingEdge(dut.clk)


def check_spad_matrix(dut, spad_num: int, expected_flat: list[int], label: str):
    for i, exp in enumerate(expected_flat):
        got = int(dut.sp_i.spad_mem[spad_num][i].value)
        assert got == exp, f"{label} spad[{spad_num}][{i}] expected {exp}, got {got}"


def check_written_matrix(
    written_memory: dict[int, int],
    base_addr: int,
    expected_flat: list[int],
    label: str
):
    for i, exp in enumerate(expected_flat):
        addr = base_addr + i
        assert addr in written_memory, f"{label} missing write to {hex(addr)}"
        got = written_memory[addr]
        assert got == exp, f"{label} at {hex(addr)} expected {exp}, got {got}"


@cocotb.test()
async def test_gemm_8x8_8bit_input_32bit_output(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    A = np.array([
        [ 1,  2,  3,  4,  5,  6,  7,  8],
        [ 9, 10, 11, 12, 13, 14, 15, 16],
        [17, 18, 19, 20, 21, 22, 23, 24],
        [25, 26, 27, 28, 29, 30, 31, 32],
        [33, 34, 35, 36, 37, 38, 39, 40],
        [41, 42, 43, 44, 45, 46, 47, 48],
        [49, 50, 51, 52, 53, 54, 55, 56],
        [57, 58, 59, 60, 61, 62, 63, 64],
    ], dtype=np.uint8)

    B = np.array([
        [64, 63, 62, 61, 60, 59, 58, 57],
        [56, 55, 54, 53, 52, 51, 50, 49],
        [48, 47, 46, 45, 44, 43, 42, 41],
        [40, 39, 38, 37, 36, 35, 34, 33],
        [32, 31, 30, 29, 28, 27, 26, 25],
        [24, 23, 22, 21, 20, 19, 18, 17],
        [16, 15, 14, 13, 12, 11, 10,  9],
        [ 8,  7,  6,  5,  4,  3,  2,  1],
    ], dtype=np.uint8)

    C = (A.astype(np.uint32) @ B.astype(np.uint32)).astype(np.uint32)

    A_flat = A.flatten().tolist()
    B_flat = B.flatten().tolist()
    C_flat = C.flatten().tolist()

    memory = {}

    # A at 0x100..0x13F
    for i, val in enumerate(A_flat):
        memory[0x100 + i] = int(val)

    # B at 0x200..0x23F
    for i, val in enumerate(B_flat):
        memory[0x200 + i] = int(val)

    written_memory = {}

    # Reset
    dut.rst.value = 1
    dut.instruction.value = 0
    dut.mem_rdata.value = 0
    dut.mem_rvalid.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # spad0 = A, spad1 = B, spad2 = C
    await run_config(dut, 0, 0x100, 8, 8)
    await run_config(dut, 1, 0x200, 8, 8)
    await run_config(dut, 2, 0x300, 8, 8)

    # Load A and B
    await run_load(dut, 0, memory)
    await run_load(dut, 1, memory)

    check_spad_matrix(dut, 0, A_flat, "A")
    check_spad_matrix(dut, 1, B_flat, "B")

    # GEMM
    await run_gemm(dut, 0, 1, 2)

    # Check full 32-bit output in spad2
    check_spad_matrix(dut, 2, C_flat, "C")

    # Store C back to memory
    await run_store(dut, 2, written_memory)

    check_written_matrix(written_memory, 0x300, C_flat, "C")

    assert len(written_memory) == 64, f"Expected 64 writes for C, got {len(written_memory)}"

    print("A =")
    print(A)
    print("B =")
    print(B)
    print("C = A @ B =")
    print(C)