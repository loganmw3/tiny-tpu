module systolic_array#(
    parameter M = 8,
    parameter N = 8,
    parameter K = 8
)(
    input  logic clk,
    input  logic rst,

    input  logic start,
    input  logic valid,

    input  logic [M-1:0][7:0] a_row,
    input  logic [N-1:0][7:0] b_col,
    output logic [M-1:0][N-1:0][31:0] c,

    output logic done
);
    localparam int CYCLES = K + M + N - 2;
    logic [$clog2(CYCLES + 1):0] ctr;

    logic clear_acc;
    logic en_acc;


    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            ctr  <= 'd0;
            done <= 'd0;
        end else begin
            done <= 'd0;

            if (start) begin
                ctr <= 'd1;
            end else if (ctr != 'd0) begin
                ctr <= ctr + 'd1;

                if (ctr == CYCLES) begin
                    done <= 'd1;
                    ctr  <= 'd0;
                end
            end
        end
    end

    assign clear_acc = start;
    assign en_acc    = valid;

    // internal forwarding wires
    logic unsigned [7:0] a_connects [M][N];
    logic unsigned [7:0] b_connects [M][N];

    generate
        for (genvar i = 0; i < M; i++) begin : rows_body
            for (genvar j = 0; j < N; j++) begin : cols_body
                mac mac_grid (
                    .clk   (clk),
                    .rst   (rst),
                    .clear (clear_acc),
                    .en    (en_acc),

                    .a_in  ((j==0) ? a_row[i] : a_connects[i][j-1]),
                    .b_in  ((i==0) ? b_col[j] : b_connects[i-1][j]),

                    .c     (c[i][j]),
                    .a_out (a_connects[i][j]),
                    .b_out (b_connects[i][j])
                );
            end
        end 
    endgenerate
endmodule : systolic_array
