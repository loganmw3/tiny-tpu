from enum import Enum

class Opcode(Enum):
    CONFIG = 0b10001
    LOAD   = 0b00111
    STORE  = 0b00110
    GEMM   = 0b11111

OPCODE_CONFIG = 0b10001
OPCODE_LOAD   = 0b00111
OPCODE_STORE  = 0b00110
OPCODE_GEMM   = 0b11111

def gen_instruction(opcode: Opcode, spad_a: int, spad_b: int, spad_c: int, ptr: int, rows: int, cols: int):
    instr = 0
    match (opcode):
        case Opcode.CONFIG:
            instr = encode_config(target_spad=spad_a, ptr=ptr, rows=rows, cols=cols)
            
        case Opcode.LOAD:
            instr = encode_load(target_spad=spad_a)
            
        case Opcode.STORE:
            instr = encode_store(target_spad=spad_c)
            
        case Opcode.GEMM:
            instr = encode_gemm(spad_a=spad_a, spad_b=spad_b, spad_c=spad_c)
        
    return instr


def encode_config(target_spad: int, ptr: int, rows: int, cols: int) -> int:
    return (
        (OPCODE_CONFIG << 59)
        | ((target_spad & 0x7) << 56)
        | ((rows & 0x3FF) << 46)
        | ((cols & 0x3FF) << 36)
        | ((ptr & 0xFFFFFFFF) << 4)
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