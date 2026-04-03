module mac (
    input  logic clk,
    input  logic rst,

    input  logic clear,   // clears accumulator for a new GEMM
    input  logic en,      // accumulate only when en=1

    input  logic unsigned [7:0]  a_in,
    input  logic unsigned [7:0]  b_in,

    output logic unsigned [31:0] c,
    output logic unsigned [7:0]  a_out,
    output logic unsigned [7:0]  b_out
);

    logic [15:0] prod;
    assign prod = a_in * b_in;

    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            c     <= '0;
            a_out <= '0;
            b_out <= '0;
        end else begin
            // forward every cycle (systolic pipeline)
            a_out <= a_in;
            b_out <= b_in;

            if (clear) begin
                c <= '0;
            end else if (en) begin
                c <= c + {16'd0, prod};
            end
        end
    end

endmodule