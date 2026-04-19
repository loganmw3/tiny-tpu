import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

from helpers.isa import encode_config, encode_gemm, encode_load, encode_store
from helpers.memory import Memory

async def start_clock(dut, period=10):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    
    
async def reset_dut(dut):
    dut.rst.value = 1
    dut.instruction.value = 0
    dut.mem_rdata.value = 0
    dut.mem_rvalid.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


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


async def run_load(dut, target_spad: int, memory: dict[int, int], timeout=120000):
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


async def run_gemm(dut, spad_a: int, spad_b: int, spad_c: int, timeout=250000):
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


async def run_store(dut, target_spad: int, memory: Memory, timeout=150000):
    dut.instruction.value = encode_store(target_spad)
    written_memory = memory.memory

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