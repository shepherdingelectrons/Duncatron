import CPUSimulator.CPU as CPU
import simple_assembler
from simple_assembler import Assembler
#import CPUSimulator.define_instructions
import pygame
import random

def prettyROM(start,stop):
    for i in range(start,stop):
        c= CPU.Memory[i]
        print(hex(i),":",hex(c),"\t",int(c),"\t",chr(c))

def showstack():
    prettyROM(0xFFFA,0x10000)

class Emulator:
    def __init__(self):
        pygame.init()
        
        fontsize = 25
        self.font = pygame.font.SysFont("couriernew",fontsize)#Font(None, 20)
        w,h = self.font.size("A") # only works for monospaced fonts
        
        self.swidth = w * 40
        self.sheight = h * 15
        self.screen = pygame.display.set_mode((self.swidth, self.sheight))

        wincolour = (255,0,0)
        self.screen.fill(wincolour)
        
        self.fx = 0
        self.fy = 0

        self.quit=False

    def printchar(self,char):
        fg = 250, 240, 230
        bg = 5, 5, 5
        
        if len(char)!=1:
            print("Error! char must be a single character!")
            return
        #text = "Fonty"
        w,h = self.font.size(char)
        ren = self.font.render(char, 0, fg, bg)
        self.screen.blit(ren, (self.fx, self.fy))
        
        self.fx+=w
        if self.fx>=self.swidth:
            self.fx=0
            self.fy+=h
        if self.fy>=self.sheight:
            #  bump up image by h
            pass
        
    def VRAM(self,bank=0):
        px,py=0,0
        off_px,off_py=100,100
        pixels = 10
        
        for i in range(0,3*256,3):
            r = CPU.Memory[0x8000+i]
            g = CPU.Memory[0x8000+i+1]
            b = CPU.Memory[0x8000+i+2]

            start_x = off_px+px*pixels
            start_y = off_py+py*pixels
            pygame.draw.rect(self.screen, (r,g,b),pygame.Rect(start_x,start_y,pixels,pixels))
            px+=1
            if px>=16:
                px=0
                py+=1
        
    def print(self,text):
        pass
    
    def pygame_handle(self):
        self.VRAM()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit=True
        return not self.quit

def randomiseRAM(memory, start,end):
    for m in range(start,end):
        memory[m]=random.randint(0,255)
        
if __name__=="__main__":
    # *********************** ASSEMBLE CODE *******************************
    print("Assembling code:")
    asm = Assembler("asm files\\testasm2.txt",CPU.Memory,"")
    #asm.instruction_str = CPUSimulator.define_instructions.instruction_str
    success = asm.assemble()
    # *********************** EMULATE CPU *******************************

    if success:
        randomiseRAM(CPU.Memory,0x8000,0x10000)
        print("Assemble OK!")
        current_pos = 0
        
        print("Emulating CPU:")
        myEmulator = Emulator()
        debug=False
        prevR3 = -1

        # Fill a buffer and then 
        uartRX = "I am typing this, hello world\b\b\b\b\b,\b \bgoodbye sweet world"+chr(13)
        uartRX += "M"+chr(0x08)+"MOV A,U\b\b"+",r5"+chr(13)
        uartRX += "A"*100+"\bB" +chr(13)
        
        while not CPU.HALT.isactive(None):
            if not myEmulator.pygame_handle():
                print("BREAKING")
                break

            CPU.CPU.compute(verbose=(( CPU.CPU.microcode_counter==1) and debug))
            
            if CPU.U_reg.value!=-1: # Bit of a hack
                print(chr(CPU.U_reg.value), end='')
                myEmulator.printchar(chr(CPU.U_reg.value))
                CPU.U_reg.value=-1

            if debug and CPU.CPU.microcode_counter==2:
                print("Loaded instruction:",asm.lookupASM[CPU.I_reg.value])
                input(">") # Wait for keypress between clock cycles
            
            # 7 6    5        4    3 2 1 0
            # X X RX_READY SENDING X N C Z
            if CPU.F_reg.value&(1<<5)==0 and uartRX!="": # if the virtual UART RX buffer is not empty
                CPU.U_reg.valueHI = ord(uartRX[0]) # then set a flag and read into U register
                CPU.F_reg.value|=(1<<5)
                uartRX=uartRX[1:] # get next character from UART string buffer

               
    ##    prettyROM(0,20)
        print("Final stack pointer=",CPU.SP.value)
        while myEmulator.pygame_handle():
            pass
        
        pygame.quit()
    ##    showstack()

