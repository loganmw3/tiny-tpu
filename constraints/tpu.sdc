# Clock definition
create_clock -name clk -period 20 [get_ports clk]

# Assume inputs arrive midway through cycle
set_input_delay 5 -clock clk [all_inputs]

# Assume outputs must be ready shortly after clock
set_output_delay 5 -clock clk [all_outputs]

# Don’t try to time reset
set_false_path -from [get_ports rst]