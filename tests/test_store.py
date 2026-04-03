import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

OPCODE_CONFIG = 0b10001
OPCODE_LOAD   = 0b00111
OPCODE_STORE  = 0b00110


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


def unpack_spad_meta(v: int) -> tuple[int, int, int, int]:
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
async def test_config_load_store(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

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

    written_memory = {}

    dut.rst.value = 1
    dut.instruction.value = 0
    dut.mem_rdata.value = 0
    dut.mem_rvalid.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # -------------------------
    # 1) CONFIG
    # -------------------------
    dut.instruction.value = encode_config(target_spad=1, ptr=0x100, rows=3, cols=3)

    await wait_for_signal(dut.commit_en, dut.clk)

    raw_meta = int(dut.metadata_regs_i.meta_mem[1].value)
    rows, cols, ptr, valid = unpack_spad_meta(raw_meta)

    assert rows == 3, f"rows mismatch: got {rows}"
    assert cols == 3, f"cols mismatch: got {cols}"
    assert ptr == 0x100, f"ptr mismatch: got {hex(ptr)}"
    assert valid == 1, f"valid mismatch: got {valid}"

    await RisingEdge(dut.clk)

    # -------------------------
    # 2) LOAD
    # -------------------------
    dut.instruction.value = encode_load(target_spad=1)

    for _ in range(100):
        await RisingEdge(dut.clk)

        if int(dut.mem_ren.value) == 1:
            addr = int(dut.mem_raddr.value)
            data = memory.get(addr, 0)
            dut.mem_rdata.value = data
            dut.mem_rvalid.value = 1
        else:
            dut.mem_rvalid.value = 0

        if int(dut.commit_en.value) == 1:
            break
    else:
        assert False, "Timeout waiting for LOAD to commit"

    dut.mem_rvalid.value = 0
    dut.mem_rdata.value = 0

    expected = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99]
    for i, exp in enumerate(expected):
        got = int(dut.sp_i.spad_mem[1][i].value)
        assert got == exp, f"spad[1][{i}] expected {hex(exp)}, got {hex(got)}"

    dut.instruction.value = 0
    await RisingEdge(dut.clk)

    # -------------------------
    # 3) STORE with debug prints
    # -------------------------
    dut.instruction.value = encode_store(target_spad=1)

    for cyc in range(200):
        await RisingEdge(dut.clk)
        await ReadOnly()

        state         = int(dut.state.value)
        idx           = int(dut.load_idx_reg.value)
        total         = int(dut.load_total_reg.value)
        ptr_reg       = int(dut.load_ptr_reg.value)
        rows_reg      = int(dut.load_rows_reg.value)
        cols_reg      = int(dut.load_cols_reg.value)
        spad_reg      = int(dut.load_spad_reg.value)

        spad_ren      = int(dut.spad_ren.value)
        spad_rspad    = int(dut.spad_rspad.value)
        spad_raddr    = int(dut.spad_raddr.value)
        spad_rdata    = int(dut.spad_rdata.value)

        mem_wen       = int(dut.mem_wen.value)
        mem_waddr     = int(dut.mem_waddr.value)
        mem_wdata     = int(dut.mem_wdata.value)

        commit        = int(dut.commit_en.value)

        print(
            f"[STORE cyc={cyc:03d}] "
            f"state={state} "
            f"idx={idx} total={total} "
            f"ptr=0x{ptr_reg:08x} rows={rows_reg} cols={cols_reg} spad={spad_reg} "
            f"| spad_ren={spad_ren} rspad={spad_rspad} raddr={spad_raddr} rdata=0x{spad_rdata:02x} "
            f"| mem_wen={mem_wen} waddr=0x{mem_waddr:08x} wdata=0x{mem_wdata:02x} "
            f"| commit={commit}"
        )

        if mem_wen == 1:
            written_memory[mem_waddr] = mem_wdata

        if commit == 1:
            print(f"STORE committed on cycle {cyc}")
            break
    else:
        assert False, "Timeout waiting for STORE to commit"

    # -------------------------
    # 4) Verify STORE writes
    # -------------------------
    for i, exp in enumerate(expected):
        addr = 0x100 + i
        assert addr in written_memory, f"STORE never wrote address {hex(addr)}"
        got = written_memory[addr]
        assert got == exp, f"STORE wrote {hex(got)} to {hex(addr)}, expected {hex(exp)}"

    assert len(written_memory) == 9, f"Expected 9 STORE writes, got {len(written_memory)}"

    # leave ReadOnly phase before driving instruction low
    await RisingEdge(dut.clk)
    dut.instruction.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.commit_en.value) == 0