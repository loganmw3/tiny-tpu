module tpu
import types::*;
#(
    parameter NUM_SPADS = 8,
    parameter SPAD_DEPTH = 256
)(
    input  logic clk,
    input  logic rst,

    input  logic [63:0] instruction,

    // Read interface with memory
    output logic [31:0] mem_raddr,
    output logic        mem_ren,
    input  logic [31:0]  mem_rdata,
    input  logic        mem_rvalid,

    output logic [31:0] mem_waddr,
    output logic [31:0]  mem_wdata,
    output logic        mem_wen,

    output logic        commit_en
);

// States
localparam IDLE            = 0;
localparam CONFIGURE       = 1;

localparam LOAD_META_REQ   = 2;
localparam LOAD_META_WAIT  = 3;
localparam LOAD_READ_REQ   = 4;
localparam LOAD_READ_WAIT  = 5;
localparam LOAD_WRITE      = 6;

localparam STORE_META_REQ  = 7;
localparam STORE_META_WAIT = 8;
localparam STORE_READ_SPAD = 9;
localparam STORE_MEM_WRITE = 10;

localparam GEMM_META_REQ   = 11;
localparam GEMM_META_WAIT  = 12;
localparam GEMM_LOAD_REQ   = 13;
localparam GEMM_LOAD_WAIT  = 14;
localparam GEMM_LOAD_STAGE = 15;
localparam GEMM_START      = 16;
localparam GEMM_RUN        = 17;
localparam GEMM_WAIT_DONE  = 18;
localparam GEMM_CAPTURE    = 19;
localparam GEMM_WRITEBACK  = 20;

localparam COMMIT          = 21;

localparam NUM_STATES      = 22;

// Opcodes
localparam OPCODE_CONFIG = 5'b10001;
localparam OPCODE_LOAD   = 5'b00111;
localparam OPCODE_STORE  = 5'b00110;
localparam OPCODE_GEMM   = 5'b11111;

// State
logic [$clog2(NUM_STATES)-1:0] state, state_next;

// Metadata
logic                         meta_mem_wen;
logic [$clog2(NUM_SPADS)-1:0] meta_mem_waddr;
spad_meta_t                   meta_mem_wdata;

logic                         meta_mem_ren;
logic [$clog2(NUM_SPADS)-1:0] meta_mem_raddr;
spad_meta_t                   meta_mem_rdata;

// Shared LOAD / STORE regs
logic [$clog2(NUM_SPADS)-1:0] load_spad_reg;
logic [31:0]                  load_ptr_reg;
logic [7:0]                   load_rows_reg;
logic [7:0]                   load_cols_reg;
logic [15:0]                  load_total_reg;
logic [15:0]                  load_idx_reg;
logic [31:0]                   load_data_reg;

// Scratchpad interface
logic                          spad_wen;
logic [$clog2(NUM_SPADS)-1:0]  spad_wspad;
logic [$clog2(SPAD_DEPTH)-1:0] spad_waddr;
logic [31:0]                   spad_wdata;

logic                          spad_ren;
logic [$clog2(NUM_SPADS)-1:0]  spad_rspad;
logic [$clog2(SPAD_DEPTH)-1:0] spad_raddr;
logic [31:0]                   spad_rdata;

// GEMM regs
logic [$clog2(NUM_SPADS)-1:0] gemm_spad_a_reg;
logic [$clog2(NUM_SPADS)-1:0] gemm_spad_b_reg;
logic [$clog2(NUM_SPADS)-1:0] gemm_spad_c_reg;

logic [31:0] gemm_a_ptr_reg, gemm_b_ptr_reg, gemm_c_ptr_reg;
logic [7:0]  gemm_a_rows_reg, gemm_a_cols_reg;
logic [7:0]  gemm_b_rows_reg, gemm_b_cols_reg;
logic [7:0]  gemm_c_rows_reg, gemm_c_cols_reg;

logic [7:0]  gemm_M_reg, gemm_N_reg, gemm_K_reg;

logic [1:0]  gemm_meta_phase_reg;
logic [1:0]  gemm_load_phase_reg;   // 0=A, 1=B, 2=done
logic [15:0] gemm_idx_reg;
logic [7:0]  gemm_t_reg;
logic [15:0] gemm_store_idx_reg;
logic [31:0]  gemm_spad_data_reg;

// stage buffers
logic [7:0]  stage_a [0:7][0:7];
logic [7:0]  stage_b [0:7][0:7];
logic [31:0] stage_c [0:7][0:7];

// temp indices for preload / writeback
logic [2:0] gemm_a_row_idx;
logic [2:0] gemm_a_col_idx;
logic [2:0] gemm_b_row_idx;
logic [2:0] gemm_b_col_idx;
logic [2:0] gemm_store_row_idx;
logic [2:0] gemm_store_col_idx;

// Systolic array interface
logic        sys_start;
logic        sys_valid;
logic [7:0]  sys_a_row [0:7];
logic [7:0]  sys_b_col [0:7];
logic [31:0] sys_c     [0:7][0:7];
logic        sys_done;


// Helper index logic
logic [15:0] gemm_a_row_idx_full;
logic [15:0] gemm_a_col_idx_full;
logic [15:0] gemm_b_row_idx_full;
logic [15:0] gemm_b_col_idx_full;
logic [15:0] gemm_store_row_idx_full;
logic [15:0] gemm_store_col_idx_full;
assign gemm_a_row_idx_full     = gemm_idx_reg       / {8'd0, gemm_a_cols_reg};
assign gemm_a_col_idx_full     = gemm_idx_reg       % {8'd0, gemm_a_cols_reg};

assign gemm_b_row_idx_full     = gemm_idx_reg       / {8'd0, gemm_b_cols_reg};
assign gemm_b_col_idx_full     = gemm_idx_reg       % {8'd0, gemm_b_cols_reg};

assign gemm_store_row_idx_full = gemm_store_idx_reg / {8'd0, gemm_c_cols_reg};
assign gemm_store_col_idx_full = gemm_store_idx_reg % {8'd0, gemm_c_cols_reg};

assign gemm_a_row_idx          = gemm_a_row_idx_full[2:0];
assign gemm_a_col_idx          = gemm_a_col_idx_full[2:0];

assign gemm_b_row_idx          = gemm_b_row_idx_full[2:0];
assign gemm_b_col_idx          = gemm_b_col_idx_full[2:0];

assign gemm_store_row_idx      = gemm_store_row_idx_full[2:0];
assign gemm_store_col_idx      = gemm_store_col_idx_full[2:0];


// Sequential logic
always_ff @(posedge clk) begin : state_machine_ff
    if (rst) begin
        state <= IDLE;

        load_spad_reg  <= '0;
        load_ptr_reg   <= '0;
        load_rows_reg  <= '0;
        load_cols_reg  <= '0;
        load_total_reg <= '0;
        load_idx_reg   <= '0;
        load_data_reg  <= '0;

        gemm_spad_a_reg     <= '0;
        gemm_spad_b_reg     <= '0;
        gemm_spad_c_reg     <= '0;

        gemm_a_ptr_reg      <= '0;
        gemm_b_ptr_reg      <= '0;
        gemm_c_ptr_reg      <= '0;
        gemm_a_rows_reg     <= '0;
        gemm_a_cols_reg     <= '0;
        gemm_b_rows_reg     <= '0;
        gemm_b_cols_reg     <= '0;
        gemm_c_rows_reg     <= '0;
        gemm_c_cols_reg     <= '0;
        gemm_M_reg          <= '0;
        gemm_N_reg          <= '0;
        gemm_K_reg          <= '0;

        gemm_meta_phase_reg <= '0;
        gemm_load_phase_reg <= '0;
        gemm_idx_reg        <= '0;
        gemm_t_reg          <= '0;
        gemm_store_idx_reg  <= '0;
        gemm_spad_data_reg  <= '0;

        for (integer i = 0; i < 8; i = i + 1) begin
            for (integer j = 0; j < 8; j = j + 1) begin
                stage_a[i][j] <= '0;
                stage_b[i][j] <= '0;
                stage_c[i][j] <= '0;
            end
        end
    end else begin
        state <= state_next;

        // LOAD / STORE
        if (state == LOAD_META_REQ || state == STORE_META_REQ) begin
            load_spad_reg <= instruction[58:56];
        end

        if (state == LOAD_META_WAIT || state == STORE_META_WAIT) begin
            load_ptr_reg   <= meta_mem_rdata.ptr;
            load_rows_reg  <= meta_mem_rdata.rows;
            load_cols_reg  <= meta_mem_rdata.cols;
            load_total_reg <= meta_mem_rdata.rows * meta_mem_rdata.cols;
            load_idx_reg   <= '0;
        end

        if (state == LOAD_READ_WAIT && mem_rvalid) begin
            load_data_reg <= mem_rdata;
        end

        if (state == LOAD_WRITE || state == STORE_MEM_WRITE) begin
            load_idx_reg <= load_idx_reg + 1'b1;
        end

        // GEMM instruction latch
        if (state == IDLE && instruction[63:59] == OPCODE_GEMM) begin
            gemm_spad_a_reg     <= instruction[58:56];
            gemm_spad_b_reg     <= instruction[55:53];
            gemm_spad_c_reg     <= instruction[52:50];
            gemm_meta_phase_reg <= 2'd0;
            gemm_load_phase_reg <= 2'd0;
            gemm_idx_reg        <= '0;
            gemm_t_reg          <= '0;
            gemm_store_idx_reg  <= '0;
        end

        // GEMM metadata capture
        if (state == GEMM_META_WAIT) begin
            case (gemm_meta_phase_reg)
                2'd0: begin
                    gemm_a_ptr_reg      <= meta_mem_rdata.ptr;
                    gemm_a_rows_reg     <= meta_mem_rdata.rows;
                    gemm_a_cols_reg     <= meta_mem_rdata.cols;
                    gemm_meta_phase_reg <= 2'd1;
                end
                2'd1: begin
                    gemm_b_ptr_reg      <= meta_mem_rdata.ptr;
                    gemm_b_rows_reg     <= meta_mem_rdata.rows;
                    gemm_b_cols_reg     <= meta_mem_rdata.cols;
                    gemm_meta_phase_reg <= 2'd2;
                end
                2'd2: begin
                    gemm_c_ptr_reg      <= meta_mem_rdata.ptr;
                    gemm_c_rows_reg     <= meta_mem_rdata.rows;
                    gemm_c_cols_reg     <= meta_mem_rdata.cols;
                    gemm_meta_phase_reg <= 2'd3;

                    gemm_M_reg <= gemm_a_rows_reg;
                    gemm_K_reg <= gemm_a_cols_reg;
                    gemm_N_reg <= gemm_b_cols_reg;

                    gemm_load_phase_reg <= 2'd0;
                    gemm_idx_reg        <= '0;
                end
                default: begin
                    gemm_meta_phase_reg <= gemm_meta_phase_reg;
                end
            endcase
        end

        // capture scratchpad read data for GEMM preload
        if (state == GEMM_LOAD_WAIT) begin
            gemm_spad_data_reg <= spad_rdata;
        end

        // write scratchpad preload data into stage_a / stage_b
        if (state == GEMM_LOAD_STAGE) begin
            if (gemm_load_phase_reg == 2'd0) begin
                stage_a[gemm_a_row_idx][gemm_a_col_idx] <= gemm_spad_data_reg[7:0];

                if (gemm_idx_reg + 1 >= (gemm_a_rows_reg * gemm_a_cols_reg)) begin
                    gemm_idx_reg        <= '0;
                    gemm_load_phase_reg <= 2'd1;
                end else begin
                    gemm_idx_reg <= gemm_idx_reg + 1'b1;
                end
            end else if (gemm_load_phase_reg == 2'd1) begin
                stage_b[gemm_b_row_idx][gemm_b_col_idx] <= gemm_spad_data_reg[7:0];

                if (gemm_idx_reg + 1 >= (gemm_b_rows_reg * gemm_b_cols_reg)) begin
                    gemm_idx_reg        <= '0;
                    gemm_load_phase_reg <= 2'd2;
                    gemm_t_reg          <= '0;
                end else begin
                    gemm_idx_reg <= gemm_idx_reg + 1'b1;
                end
            end
        end

        // GEMM feed counter
        // GEMM feed time counter
        if (state == GEMM_START) begin
            gemm_t_reg <= 8'd0;
        end else if (state == GEMM_RUN) begin
            gemm_t_reg <= gemm_t_reg + 1'b1;
        end

        // capture systolic outputs into stage_c after done
        if (state == GEMM_CAPTURE) begin
            for (integer i = 0; i < 8; i = i + 1) begin
                for (integer j = 0; j < 8; j = j + 1) begin
                    stage_c[i][j] <= sys_c[i][j];
                end
            end
            gemm_store_idx_reg <= '0;
        end

        // serialize stage_c back into scratchpad C
        if (state == GEMM_WRITEBACK) begin
            gemm_store_idx_reg <= gemm_store_idx_reg + 1'b1;
        end
    end
end

always_comb begin : state_machine_comb
    state_next = state;

    // main memory defaults
    mem_raddr = '0;
    mem_ren   = 1'b0;
    mem_waddr = '0;
    mem_wdata = '0;
    mem_wen   = 1'b0;

    // metadata defaults
    meta_mem_ren   = 1'b0;
    meta_mem_raddr = '0;
    meta_mem_wen   = 1'b0;
    meta_mem_waddr = '0;
    meta_mem_wdata = '0;

    // commit default
    commit_en = 1'b0;

    // scratchpad defaults
    spad_wen   = 1'b0;
    spad_wspad = '0;
    spad_waddr = '0;
    spad_wdata = '0;

    spad_ren   = 1'b0;
    spad_rspad = '0;
    spad_raddr = '0;

    // systolic defaults
    sys_start = 1'b0;
    sys_valid = 1'b0;
    for (integer k = 0; k < 8; k = k + 1) begin
        sys_a_row[k] = '0;
        sys_b_col[k] = '0;
    end

    case (state)
        IDLE: begin
            case (instruction[63:59])
                OPCODE_CONFIG: state_next = CONFIGURE;
                OPCODE_LOAD:   state_next = LOAD_META_REQ;
                OPCODE_STORE:  state_next = STORE_META_REQ;
                OPCODE_GEMM:   state_next = GEMM_META_REQ;
                default:       state_next = IDLE;
            endcase
        end

        // CONFIG
        CONFIGURE: begin
            meta_mem_wen         = 1'b1;
            meta_mem_waddr       = instruction[58:56];
            meta_mem_wdata.ptr   = instruction[47:16];
            meta_mem_wdata.rows  = instruction[15:8];
            meta_mem_wdata.cols  = instruction[7:0];
            meta_mem_wdata.valid = 1'b1;
            state_next           = COMMIT;
        end

        // LOAD
        LOAD_META_REQ: begin
            meta_mem_ren   = 1'b1;
            meta_mem_raddr = instruction[58:56];
            state_next     = LOAD_META_WAIT;
        end

        LOAD_META_WAIT: begin
            state_next = LOAD_READ_REQ;
        end

        LOAD_READ_REQ: begin
            mem_ren   = 1'b1;
            mem_raddr = load_ptr_reg + {16'd0, load_idx_reg};
            state_next = LOAD_READ_WAIT;
        end

        LOAD_READ_WAIT: begin
            state_next = mem_rvalid ? LOAD_WRITE : LOAD_READ_WAIT;
        end

        LOAD_WRITE: begin
            spad_wen   = 1'b1;
            spad_wspad = load_spad_reg;
            spad_waddr = load_idx_reg[$clog2(SPAD_DEPTH)-1:0];
            spad_wdata = load_data_reg;

            if (load_idx_reg + 16'd1 >= load_total_reg)
                state_next = COMMIT;
            else
                state_next = LOAD_READ_REQ;
        end

        // STORE
        STORE_META_REQ: begin
            meta_mem_ren   = 1'b1;
            meta_mem_raddr = instruction[58:56];
            state_next     = STORE_META_WAIT;
        end

        STORE_META_WAIT: begin
            state_next = STORE_READ_SPAD;
        end

        STORE_READ_SPAD: begin
            spad_ren   = 1'b1;
            spad_rspad = load_spad_reg;
            spad_raddr = load_idx_reg[$clog2(SPAD_DEPTH)-1:0];
            state_next = STORE_MEM_WRITE;
        end

        STORE_MEM_WRITE: begin
            mem_wen   = 1'b1;
            mem_waddr = load_ptr_reg + {16'd0, load_idx_reg};
            mem_wdata = spad_rdata;

            if (load_idx_reg + 16'd1 >= load_total_reg)
                state_next = COMMIT;
            else
                state_next = STORE_READ_SPAD;
        end

        // GEMM metadata reads
        GEMM_META_REQ: begin
            meta_mem_ren = 1'b1;
            case (gemm_meta_phase_reg)
                2'd0: meta_mem_raddr = gemm_spad_a_reg;
                2'd1: meta_mem_raddr = gemm_spad_b_reg;
                2'd2: meta_mem_raddr = gemm_spad_c_reg;
                default: meta_mem_raddr = '0;
            endcase
            state_next = GEMM_META_WAIT;
        end

        GEMM_META_WAIT: begin
            if (gemm_meta_phase_reg == 2'd3)
                state_next = GEMM_LOAD_REQ;
            else
                state_next = GEMM_META_REQ;
        end

        // GEMM preload from spads into stage_a / stage_b
        GEMM_LOAD_REQ: begin
            spad_ren = 1'b1;

            if (gemm_load_phase_reg == 2'd0) begin
                spad_rspad = gemm_spad_a_reg;
                spad_raddr = gemm_idx_reg[$clog2(SPAD_DEPTH)-1:0];
            end else begin
                spad_rspad = gemm_spad_b_reg;
                spad_raddr = gemm_idx_reg[$clog2(SPAD_DEPTH)-1:0];
            end

            state_next = GEMM_LOAD_WAIT;
        end

        GEMM_LOAD_WAIT: begin
            state_next = GEMM_LOAD_STAGE;
        end

        GEMM_LOAD_STAGE: begin
            if (gemm_load_phase_reg == 2'd2)
                state_next = GEMM_START;
            else
                state_next = GEMM_LOAD_REQ;
        end

        // GEMM feed systolic array
        GEMM_START: begin
            sys_start = 1'b1;
            sys_valid = 1'b1;

            for (integer i = 0; i < 8; i = i + 1) begin
                if ((i < gemm_M_reg) && (0 >= i) && ((0 - i) < gemm_K_reg))
                    sys_a_row[i] = stage_a[i][0 - i];
                else
                    sys_a_row[i] = 8'd0;
            end

            for (integer j = 0; j < 8; j = j + 1) begin
                if ((j < gemm_N_reg) && (0 >= j) && ((0 - j) < gemm_K_reg))
                    sys_b_col[j] = stage_b[0 - j][j];
                else
                    sys_b_col[j] = 8'd0;
            end

            state_next = GEMM_RUN;
        end

        GEMM_RUN: begin
            sys_valid = 1'b1;

            for (integer i = 0; i < 8; i = i + 1) begin
                logic [7:0] i_u8;
                logic [7:0] a_idx;

                i_u8 = i[7:0];
                a_idx = gemm_t_reg - i_u8;
                if ((i_u8 < gemm_M_reg) && (gemm_t_reg >= i_u8) && (a_idx < gemm_K_reg))
                    sys_a_row[i] = stage_a[i][a_idx[2:0]];
                else
                    sys_a_row[i] = 8'd0;
            end

            for (integer j = 0; j < 8; j = j + 1) begin
                logic [7:0] j_u8;
                logic [7:0] b_idx;

                j_u8 = j[7:0];
                b_idx = gemm_t_reg - j_u8;
                if ((j_u8 < gemm_N_reg) && (gemm_t_reg >= j_u8) && (b_idx < gemm_K_reg))
                    sys_b_col[j] = stage_b[b_idx[2:0]][j];
                else
                    sys_b_col[j] = 8'd0;
            end

            if (gemm_t_reg + 1 >= (gemm_K_reg + gemm_M_reg + gemm_N_reg - 2))
                state_next = GEMM_WAIT_DONE;
            else
                state_next = GEMM_RUN;
        end

        GEMM_WAIT_DONE: begin
            if (sys_done)
                state_next = GEMM_CAPTURE;
            else
                state_next = GEMM_WAIT_DONE;
        end

        GEMM_CAPTURE: begin
            state_next = GEMM_WRITEBACK;
        end

        // GEMM writeback into scratchpad C
        // first-pass: truncate 32-bit result to 8 bits
        GEMM_WRITEBACK: begin
            spad_wen   = 1'b1;
            spad_wspad = gemm_spad_c_reg;
            spad_waddr = gemm_store_idx_reg[$clog2(SPAD_DEPTH)-1:0];
            spad_wdata = stage_c[gemm_store_row_idx][gemm_store_col_idx];

            if (gemm_store_idx_reg + 1 >= (gemm_M_reg * gemm_N_reg))
                state_next = COMMIT;
            else
                state_next = GEMM_WRITEBACK;
        end

        // COMMIT
        COMMIT: begin
            commit_en  = 1'b1;
            state_next = IDLE;
        end

        default: begin
            state_next = IDLE;
        end
    endcase
end

// Metadata
metadata_regs #(
    .NUM_SPADS(NUM_SPADS)
) metadata_regs_i (
    .clk(clk),
    .rst(rst),

    .meta_mem_ren(meta_mem_ren),
    .meta_mem_raddr(meta_mem_raddr),
    .meta_mem_rdata(meta_mem_rdata),

    .meta_mem_wen(meta_mem_wen),
    .meta_mem_waddr(meta_mem_waddr),
    .meta_mem_wdata(meta_mem_wdata)
);

// Scratchpad
scratchpad #(
    .NUM_SPADS(NUM_SPADS),
    .SPAD_DEPTH(SPAD_DEPTH)
) sp_i (
    .clk(clk),
    .rst(rst),

    .spad_wen(spad_wen),
    .spad_wspad(spad_wspad),
    .spad_waddr(spad_waddr),
    .spad_wdata(spad_wdata),

    .spad_ren(spad_ren),
    .spad_rspad(spad_rspad),
    .spad_raddr(spad_raddr),
    .spad_rdata(spad_rdata)
);

// Systolic array
systolic_array #(
    .N(8),
    .K(8)
) sys_arr (
    .clk(clk),
    .rst(rst),
    .start(sys_start),
    .valid(sys_valid),
    .a_row(sys_a_row),
    .b_col(sys_b_col),
    .c(sys_c),
    .done(sys_done)
);

endmodule : tpu