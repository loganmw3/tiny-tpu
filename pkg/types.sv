package types;

typedef struct packed {
    logic [31:0] ptr;
    logic [9:0]  rows;
    logic [9:0]  cols;
    logic        valid;
} spad_meta_t;

endpackage