from CPUSimulator.simple_assembler import Assembler
import CPUSimulator.CPU
import CPUSimulator.define_instructions
import Duncatron_C_compiler
from optimise_asm import Optimiser

text=r"""
    int var69=69;
    int hello=world=3;
    int f = 2;
    int a = 1+2;
    int b = a+f+3;
    int g = f+(2+3);
    int h = (1+2)+3;
    int i = j=((a-9)+(2+5))+((3+0)+(4+250));

    void function(void)
    {
        a=0;
    }

    int q = 5;
    
    void main()
    {
        int c=65;
        while(c<65+26-1)
        {
       #pragma asm("mov A,%0",c)
       #pragma asm("mov U,A")
       c=c+1;
       }
      
    }

    void putchar(int c)
    {
    int c=23;
    #pragma asm("mov A,%0",c)
    #pragma asm("mov U,A")
    #pragma asm("mov A,%0",0x01)
    #pragma asm("mov %0,A",c)
    }
    """

print("Compiling C code...")
mycompiler = Duncatron_C_compiler.Compiler()
ASMcode = mycompiler.compile(text,verbose=False) 
print(ASMcode)
print("Optimising assembly")
asmOptimiser = Optimiser(Duncatron_C_compiler.temp_regs)
ASMcode = asmOptimiser.optimise_code(ASMcode)
print(ASMcode)
print("Assembling to machine code")

asm = Assembler(None,CPUSimulator.CPU.Memory,ASMcode)
asm.instruction_str = CPUSimulator.define_instructions.instruction_str
success = asm.assemble()
if success:
    print("Machine code generated, simulating")
    # The CPU simulator needs cleaning up with a clean instance
    while not CPUSimulator.CPU.HALT.isactive(None):
        CPUSimulator.CPU.CPU.compute()
        if CPUSimulator.CPU.U_reg.value!=-1: # Bit of a hack
                print(chr(CPUSimulator.CPU.U_reg.value), end='')
                CPUSimulator.CPU.U_reg.value=-1
    print("Final stack pointer=",CPUSimulator.CPU.SP.value)
else:
    print("Error: Bad assembly")
