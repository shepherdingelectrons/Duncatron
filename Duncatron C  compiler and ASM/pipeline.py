import Duncatron_C_compiler
from optimise_asm import Optimiser
from simple_assembler import Assembler
import CPUSimulator.CPU as CPU


text=r"""   
    void main()
    {
        #pragma asm("mov A,0x45")
       #pragma asm("mov U,A")
       
        int c=65,d=1;
        while(c<65+26-1)
        {
       #pragma asm("mov A,%0",c)
       #pragma asm("mov U,A")
       c+=d;
       }

        for (c=65+26-1;c>=65;c-=1)
        {
        #pragma asm("mov A,%0",c)
        #pragma asm("mov U,A")
        }
       
      
    }
    """

def prettyROM(start,stop):
    for i in range(start,stop):
        c= CPU.Memory[i]
        print(hex(i),":",hex(c),"\t",int(c),"\t",chr(c))
        
print("Compiling C code...")
mycompiler = Duncatron_C_compiler.Compiler()
ASMcode = mycompiler.compile(text,verbose=False)
print(ASMcode)
print("Optimising assembly")
asmOptimiser = Optimiser(Duncatron_C_compiler.temp_regs)
optimised_ASMcode = asmOptimiser.optimise_code(ASMcode)
print(optimised_ASMcode)
print("Assembling to machine code")
CPU.reset() # wipes memory (by default) and restores state
asm = Assembler(None,CPU.Memory,optimised_ASMcode) # We pass on the CPU Memory so that
# the machine code can be put into it for simulation

if asm.assemble():
    print("Machine code generated, simulating")
    while not CPU.HALT.isactive(None):
        CPU.CPU.compute()
        if CPU.U_reg.value!=-1:
                print(chr(CPU.U_reg.value), end='')
                CPU.U_reg.value=-1
    print("Final stack pointer=",CPU.SP.value)
else:
    print("Error: Bad assembly")

