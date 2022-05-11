import CPU
import simple_assembler
from simple_assembler import Assembler
import define_instructions

def prettyROM(start,stop):
    for i in range(start,stop):
        c= CPU.Memory[i]
        print(hex(i),":",hex(c),"\t",int(c),"\t",chr(c))

def showstack():
    prettyROM(0xFFFA,0x10000)

if __name__=="__main__":
        
    # *********************** ASSEMBLE CODE *******************************
    print("Assembling code:")
    asm = Assembler("testASM0.txt",CPU.Memory,"")
    asm.instruction_str = define_instructions.instruction_str
    success = asm.assemble()
    # *********************** EMULATE CPU *******************************

    if success:
        print("Assemble OK!")
        current_pos = 0
        
        print("Emulating CPU:")
        debug=0
        prevR3 = -1

        # Fill a buffer and then 
        uartRX = "I am typing this, hello world\b\b\b\b\b,\b \bgoodbye sweet world"+chr(13)
        uartRX += "M"+chr(0x08)+"MOV A,U\b\b"+",r5"+chr(13)
        uartRX += "A"*100+"\bB" +chr(13)
        
        while not CPU.HALT.isactive(None):
            if debug: print("Loaded instruction:",assembler.lookupASM(CPU.I_reg.value))

            CPU.CPU.compute(verbose=debug)
            
            if CPU.U_reg.value!=-1: # Bit of a hack
                print(chr(CPU.U_reg.value), end='')
                CPU.U_reg.value=-1

            if debug: input(">") # Wait for keypress between clock cycles
            
            # 7 6    5        4    3 2 1 0
            # X X RX_READY SENDING X N C Z
            if CPU.F_reg.value&(1<<5)==0 and uartRX!="": # if the virtual UART RX buffer is not empty
                CPU.U_reg.valueHI = ord(uartRX[0]) # then set a flag and read into U register
                CPU.F_reg.value|=(1<<5)
                uartRX=uartRX[1:] # get next character from UART string buffer

               
    ##    prettyROM(0,20)
        print("Final stack pointer=",CPU.SP.value)
    ##    showstack()

