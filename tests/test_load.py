import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

OPCODE_CONFIG = 0b10001
OPCODE_LOAD   = 0b00111


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


def unpack_spad_meta(v: int) -> tuple[int, int, int, int]:
    # struct packed order:
    # rows[48:41], cols[40:33], ptr[32:1], valid[0]
    valid = v & 0x1
    ptr   = (v >> 1) & 0xFFFFFFFF
    cols  = (v >> 33) & 0xFF
    rows  = (v >> 41) & 0xFF
    return rows, cols, ptr, valid


async def wait_for_signal(signal, clk, timeout=50):
    for _ in range(timeout):
        await RisingEdge(clk)
        await ReadOnly()
        if int(signal.value) == 1:
            return
    assert False, f"Timeout waiting for {signal._name}"


@cocotb.test()
async def test_config_and_load(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Fake byte-addressed memory
    memory = {
        0x100: 0x11,
        0x101: 0x22,
        0x102: 0x33,
        0x103: 0x44,
        0x104: 0x55,
        0x105: 0x66,
        0x106: 0x77,
        0x107: 0x88,
        0x108: 0x99,
        
    }

    # Reset / defaults
    dut.rst.value = 1
    dut.instruction.value = 0
    dut.mem_rdata.value = 0
    dut.mem_rvalid.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # -------------------------
    # 1) CONFIG scratchpad 1
    # ptr = 0x100, rows=2, cols=2
    # -------------------------
    encode_instruction = encode_config(target_spad=1, ptr=0x100, rows=3, cols=3)
    dut.instruction.value = encode_instruction

    await wait_for_signal(dut.commit_en, dut.clk)

    raw_meta = int(dut.metadata_regs_i.meta_mem[1].value)
    rows, cols, ptr, valid = unpack_spad_meta(raw_meta)

    assert rows == 3, f"rows mismatch: got {rows}"
    assert cols == 3, f"cols mismatch: got {cols}"
    assert ptr == 0x100, f"ptr mismatch: got {hex(ptr)}"
    assert valid == 1, f"valid mismatch: got {valid}"

    # Drop instruction after commit
    await RisingEdge(dut.clk)
    # await ReadOnly()


    # -------------------------
    # 2) LOAD scratchpad 1
    # -------------------------
    dut.instruction.value = encode_load(target_spad=1)

    # Serve memory reads until commit
    for _ in range(100):
        await RisingEdge(dut.clk)
        # await ReadOnly()

        if int(dut.mem_ren.value) == 1:
            addr = int(dut.mem_raddr.value)
            data = memory.get(addr, 0)

            # Drive returned data for the next cycle
            dut.mem_rdata.value = data
            dut.mem_rvalid.value = 1
        else:
            dut.mem_rvalid.value = 0

        if int(dut.commit_en.value) == 1:
            break
    else:
        assert False, "Timeout waiting for LOAD to commit"

    # Clear memory response
    dut.mem_rvalid.value = 0
    dut.mem_rdata.value = 0

    # -------------------------
    # 3) Check scratchpad contents
    # -------------------------
    got0 = int(dut.sp_i.spad_mem[1][0].value)
    got1 = int(dut.sp_i.spad_mem[1][1].value)
    got2 = int(dut.sp_i.spad_mem[1][2].value)
    got3 = int(dut.sp_i.spad_mem[1][3].value)
    got4 = int(dut.sp_i.spad_mem[1][4].value)
    got5 = int(dut.sp_i.spad_mem[1][5].value)
    got6 = int(dut.sp_i.spad_mem[1][6].value)
    got7 = int(dut.sp_i.spad_mem[1][7].value)
    got8 = int(dut.sp_i.spad_mem[1][8].value)

    assert got0 == 0x11, f"spad[1][0] expected 0x11, got {hex(got0)}"
    assert got1 == 0x22, f"spad[1][1] expected 0x22, got {hex(got1)}"
    assert got2 == 0x33, f"spad[1][2] expected 0x33, got {hex(got2)}"
    assert got3 == 0x44, f"spad[1][3] expected 0x44, got {hex(got3)}"
    assert got4 == 0x55, f"spad[1][4] expected 0x55, got {hex(got4)}"
    assert got5 == 0x66, f"spad[1][5] expected 0x66, got {hex(got5)}"
    assert got6 == 0x77, f"spad[1][6] expected 0x77, got {hex(got6)}"
    assert got7 == 0x88, f"spad[1][7] expected 0x88, got {hex(got7)}"
    assert got8 == 0x99, f"spad[1][8] expected 0x99, got {hex(got8)}"

    # commit should fall on the next cycle
    dut.instruction.value = 0
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.commit_en.value) == 0