module metadata_regs
import types::*;
#(
    parameter NUM_SPADS = 8
)(
    input logic clk,
    input logic rst,

    input logic meta_mem_ren,
    input logic [$clog2(NUM_SPADS)-1:0] meta_mem_raddr,

    input logic meta_mem_wen,
    input logic [$clog2(NUM_SPADS)-1:0] meta_mem_waddr,

    input spad_meta_t meta_mem_wdata,
    output spad_meta_t meta_mem_rdata
);

spad_meta_t meta_mem [NUM_SPADS];

always_ff @(posedge clk) begin : scratchpad_metadata
    if(rst) begin
        for(integer i=0; i< NUM_SPADS; i++) meta_mem[i] <= '0;
        meta_mem_rdata <= '0;
    end else begin
        if(meta_mem_ren) meta_mem_rdata <= meta_mem[meta_mem_raddr];
        if(meta_mem_wen) meta_mem[meta_mem_waddr] <= meta_mem_wdata;
    end
end

endmodule : metadata_regs