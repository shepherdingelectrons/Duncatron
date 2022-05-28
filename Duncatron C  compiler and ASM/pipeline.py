import Duncatron_C_compiler
from optimise_asm import Optimiser
from simple_assembler import Assembler
import CPUSimulator.CPU as CPU


text=r"""   
     void main()
    {
       int c=65,d=1;

       while(c<=90)
        {
       #pragma asm("mov A,%0",c)
       #pragma asm("mov U,A")
       c+=d;
       }

        if (c>90)
        {
        #pragma asm("mov U,0x40")
        }
        if (90<=c && d==1)
        {
        #pragma asm("mov U,0x40")
        }

        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")
        do{
        #pragma asm("mov U,0x41")
        d++;
        }
        while (d<25);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")
        
        d=1;
        do{
        #pragma asm("mov U,0x41")
        d++;
        }
        while (25>d);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")

        d=1;
        do{
        #pragma asm("mov U,0x41")
        }
        while (d++<25);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")

        d=1;
        do{
        #pragma asm("mov U,0x41")
        }
        while (25>d++);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")

        d=1;
        do{
        #pragma asm("mov U,0x41")
        }
        while (26-1>d++);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")

        d=1;
        do{
        #pragma asm("mov U,0x41")
        }
        while (d++<24+1);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")

        d=1;
        do{
        #pragma asm("mov U,0x41")
        }
        while ((1+d++)<26);
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")

        d=1;
        do{
        #pragma asm("mov U,0x41")
        }
        while ((1+d++)<(14+12));
        #pragma asm("mov A,%0",d)
        #pragma asm("mov B,0x41")
        #pragma asm("add A,B")
        #pragma asm("mov U,A")
        #pragma asm("mov U,0x0A")
        #pragma asm("mov U,0x0D")
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

