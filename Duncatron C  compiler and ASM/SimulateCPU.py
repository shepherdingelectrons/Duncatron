import CPUSimulator.CPU as CPU
import simple_assembler
import CPUSimulator.Console as Console

if __name__=="__main__":
    myCPU = CPU.Computer() # Multiple CPUs are possible, I think pygame only easily supports a single console window however

    # *********************** ASSEMBLE CODE *******************************
    print("Assembling code:")
    asm = simple_assembler.Assembler("test.asm",myCPU.Memory)
    success = asm.assemble(show_labels = False)
    # *********************** EMULATE CPU *******************************

    if success:
        print("Assemble OK!")
        print("Emulating CPU:")

        myConsole = Console.ConsoleEmulator()
        myCPU.connectConsole(myConsole)
    
        debug=False
        CPU_UP=True
        myCPU.randomiseRAM(0x8000,0x10000)
        
        while CPU_UP:
            if myCPU.HALT.isactive(None) or myConsole.pygame_handle(): CPU_UP = False
            myCPU.CPU.compute(verbose=(( myCPU.CPU.microcode_counter==1) and debug))

        print("Final stack pointer=",myCPU.SP.value)

        myConsole.close()
    else:
        print("Error compiling code")
