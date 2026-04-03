import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge

OPCODE_CONFIG = 0b10001  # instruction[63:59]


def unpack_spad_meta(v: int) -> tuple[int, int, int, int]:
    """types::spad_meta_t packed order: rows, cols, ptr, valid (valid is LSB)."""
    valid = v & 1
    ptr = (v >> 1) & 0xFFFFFFFF
    cols = (v >> 33) & 0xFF
    rows = (v >> 41) & 0xFF
    return rows, cols, ptr, valid


def encode_config(target_spad: int, ptr: int, rows: int, cols: int) -> int:
    return (
        (OPCODE_CONFIG << 59)
        | ((target_spad & 0x7) << 56)
        | ((ptr & 0xFFFF)) << 16
        | ((rows & 0xFF) << 8)
        | (cols & 0xFF)
    )


@cocotb.test()
async def test_config_operand(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.rst.value = 1
    dut.instruction.value = 0
    dut.mem_rdata.value = 0
    dut.mem_rvalid.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # CONFIG scratchpad 1: rows=0x12, cols=0x34
    dut.instruction.value = encode_config(1, 0xAAAA, 0x12, 0x34)
    # wait for commit
    for _ in range(20):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.commit_en.value) == 1:
            break
    else:
        assert False, "Timeout waiting for commit_en"

    assert int(dut.commit_en.value) == 1, "commit_en high in COMMIT state"

    raw = int(dut.metadata_regs_i.meta_mem[1].value)
    rows, cols, ptr, valid = unpack_spad_meta(raw)
    assert rows == 0x12
    assert cols == 0x34
    assert ptr == 0xAAAA
    assert valid == 1

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.commit_en.value) == 0
