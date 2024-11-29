import CPUSimulator.CPU as CPU
import simple_assembler
import CPUSimulator.define_instructions
import CPUSimulator.Console as Console

def programComputer(Computer,asm_file,show_labels=False):
    print("Assembling code:")
    asm = simple_assembler.Assembler(asm_file,Computer.Memory)
    success = asm.assemble()
    
    if show_labels:
        for lab in asm.labels:
            print(lab,":",hex(asm.labels[lab]),asm.labels[lab])

    if success:
        Computer.randomiseRAM(0x8000,0x10000)

    return success
    
if __name__=="__main__":
    myCPU = CPU.Computer() # Multiple CPUs are possible, I think pygame only easily supports a single console window however
    myConsole = Console.ConsoleEmulator()
    myCPU.connectConsole(myConsole)
        
    # *********************** ASSEMBLE CODE *******************************
    success = programComputer(myCPU,"test.asm",True)
    # *********************** EMULATE CPU *******************************

    if success:
        print("Assemble OK!")
        print("Emulating CPU:")
        
        debug=False
        CPU_UP=True

        while CPU_UP:
            if myCPU.HALT.isactive(None) or myEmulator.pygame_handle(): CPU_UP = False
            myCPU.CPU.compute(verbose=(( myCPU.CPU.microcode_counter==1) and debug))

        print("Final stack pointer=",myCPU.SP.value)

        Console.close()

