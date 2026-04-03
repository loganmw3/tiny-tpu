TOPLEVEL_LANG = verilog
SIM = verilator

PWD := $(shell pwd)
PROJ := $(abspath $(PWD)/..)

VERILOG_SOURCES += $(PROJ)/pkg/types.sv
VERILOG_SOURCES += $(PROJ)/hdl/metadata_regs.sv
VERILOG_SOURCES += $(PROJ)/hdl/scratchpad.sv
VERILOG_SOURCES += $(PROJ)/hdl/systolic_array.sv
VERILOG_SOURCES += $(PROJ)/hdl/mac.sv
VERILOG_SOURCES += $(PROJ)/hdl/tpu.sv

TOPLEVEL = tpu

export PYTHONPATH := $(PROJ)/tests

EXTRA_ARGS += -Wno-fatal
EXTRA_ARGS += --trace --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: test_config test_load

test_config:
	$(MAKE) --no-print-directory sim COCOTB_TEST_MODULES=test_config

test_load:
	$(MAKE) --no-print-directory sim COCOTB_TEST_MODULES=test_load

test_store:
	$(MAKE) --no-print-directory sim COCOTB_TEST_MODULES=test_store

test_gemm:
	$(MAKE) --no-print-directory sim COCOTB_TEST_MODULES=test_gemm