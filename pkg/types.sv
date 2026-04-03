package types;

  typedef struct packed {
    logic [7:0]  rows;
    logic [7:0]  cols;
    logic [31:0] ptr;
    logic        valid;
  } spad_meta_t;

endpackage