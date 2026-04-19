just going to jot some stuff down

the way I want to run the systolic array is by using something like this for my ISA

LOAD A
LOAD B
GEMM
STORE C

I want the instruction of LOAD A to contain the following, opcode, witdh of matrix (5 bits), height of matrix(5 bits) and a pointer to the matrix data in memory. So whenever we have a load A instruction we know how many times we need to load into the scratchpad. The rows and cols will get their own registers. This means we can have a 32x32 matrix ad the most.

I think to do this I am going to do 64 bit instructions

#change of heart

Ok already having a change of heart
So I will actually run a sequence of commands like this
CONFIG A
LOAD A
CONFIG B
LOAD B
CONFIG C
GEMM
STORE C

So Config would look something like this (we are going to say ISA is 64 Bits)
Bits [63:59] 5 bits for Opcode (allows for 32 instructions) (Congig Opcode (10001))
Bits [58:56] Target Scratchpad (for now we will do 0=A, 1=B, 2=C)
Bits [47:16] Data Pointer
Bits [15:8] Config rows 8bits
Bits [7:0] Config cols 8bits
All other bits reserved [55:16]

Loads and Stores would look like this
A Load will copy rows*cols from memory into the target scratchpad
A Store will copy rows*cols from target scratchpad into memory
row\*cols will be decided from the config registers
Bits [63:59] 5 Bits for Opcode (Load (00111), Store (00110))
Bits [58:56] Target scratchpad
Bits [31:0] 32 Bits for a pointer to the matrix memory
All other bits reserved [55:32]

GEMM would look like this
Bits [63:59] 5 Bits for Opcode (GEMM Opcode (11111))
Bits [58:56] 3 Bits for src scratchpad
Bits [55:53] 3 Bits for src scratchpad
Bits [52:50] 3 Bits for dst scratchpad
all other bits reserved [49:0]

Now I want to define the interface for the toplevel of the TPU
Off the top of my head I need
clk (1bit)
rst (1bit)

The instruction (64bits)
Read memory address (32bits)
Read memory data (8bits)
Read memory enable (1 bit)
Read memory valid (1 bit)

Write memory Address (32bits)
write memory data (8bits)
write memory data enable (1bit)

Commit signal (to tell signal that we are done with an instruction high for one cycle) (also 1 bit)

Next. I want to think about all the different units I need.
Im going to need scratchpads
Im going to need metadata registers for the scratchpad that holds the config rows and cols as well as a register to hold the pointer
Im going to need a FSM to tell which state we are in.
Im also going to need some way to feed the systolic array (I believe this is going to be a big hurdle)
Also going to need a way to write back from the systolic array into the scratchpad

Some things I eventually want to fix/change (In no specific order)

1. The memory system. Right now it is "Magic" Meaning 1 cycle response time always. Meaning the scratchpads arent really doing anything right now in terms of efficiency.
2. Parameterize the entire thing. (Atleast as much as I can)
3. Create a better interface for running code (lexer maybe idrk)
4. More Ops/control flow
5. Pipeline it (Error checks. Prolly going to need a global stall because of sys array time)
6. End goal is to run MNIST digits
7. Add/use valid bits for power
8. Maybe on a load also store into the stage and mark it somehow
9. Update the widths. (truncated to 8b)
10. Better testing suite

Ok Let me think about how I want to do this test bench for Version2

I should probably make a memory class
members should be the dictionary
and functions can be

1. init
2. Like a range check probably (valid loads and stores)
3. Single reads/ writes
4. Array reads/writes

What else do I want
I definitely want a matrix generation class
Members should be rows, cols, and vals (in a list)

Also want a instruction generator thing. This will be used to loop through as like a pseudo program
So like I can pass an array through and it will loop through each instruction and execute it

Probably want something that will print/log A/B/C/spads/whatevers

Also going to want a single function that will run an entire instruction based on the specific instruction. I think. Allow me to ponder for a little bit longer...

ISA 2.0
CONFIG:
[63:59] opcode
[58:56] target scratchpad
[55:46] rows (10 bits)
[45:36] cols (10 bits)
[35:4] pointer (32 bits)
[3:0] reserved

LOAD/STORE
[63:59] opcode
[58:56] target scratchpad
[55:0] everything else reserved

GEMM
[63:59] opcode
[58:56] src A
[55:53] src B
[52:50] dst C
[49:0] reserved
