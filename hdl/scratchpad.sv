module scratchpad #(
    parameter int NUM_SPADS  = 8,
    parameter int SPAD_DEPTH = 256
)(
    input  logic clk,
    input  logic rst,

    input  logic                              spad_wen,
    input  logic [$clog2(NUM_SPADS)-1:0]      spad_wspad,
    input  logic [$clog2(SPAD_DEPTH)-1:0]     spad_waddr,
    input  logic [31:0]                        spad_wdata,

    input  logic                              spad_ren,
    input  logic [$clog2(NUM_SPADS)-1:0]      spad_rspad,
    input  logic [$clog2(SPAD_DEPTH)-1:0]     spad_raddr,
    output logic [31:0]                        spad_rdata
);

    logic [31:0] spad_mem [NUM_SPADS][SPAD_DEPTH];

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < NUM_SPADS; i++) begin
                for (int j = 0; j < SPAD_DEPTH; j++) begin
                    spad_mem[i][j] <= '0;
                end
            end
            spad_rdata <= '0;
        end else begin
            if (spad_wen) spad_mem[spad_wspad][spad_waddr] <= spad_wdata;

            if (spad_ren) spad_rdata <= spad_mem[spad_rspad][spad_raddr];
        end
    end

endmodule : scratchpad