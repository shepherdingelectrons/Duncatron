from pyb import Pin
import random
import pyb

# Make Microsecond timer
def microwait(duration):
    micros.counter(0)
    while micros.counter()<duration:
        pass

SignalList = []

DEBUG = False
SPEED = 10#  Hz-ish

class Signal: # Signal is basically a Pin object but with an associated active_low value
    def __init__(self,label,pinLabel, pinMode,active_low):
        self.active_low = active_low
        self.pin = None
        # pinMode is Pin.OUT_PP or Pin.IN
        if active_low == True:
            PULL_UP_DOWN = Pin.PULL_UP # An active low pin, so pull_up to ensure pin is low by default
            initial_state = 1
        else:
            PULL_UP_DOWN = Pin.PULL_DOWN # active high pin, so use pull down resistors
            initial_state = 0
           
        p = Pin(pinLabel, pinMode, PULL_UP_DOWN)        
        self.pin = p
        #self.debug = True #CLK.getattr(p,"DEBUG",None)

        if p==None:
            print("Error, pin is None")
            return
        
        #p.value(initial_state) # Sometimes, pull up/down resistors don'tt always seem to work for all pins to set an initial state
        self.label = label
        self.off()
        

        if pinMode is not Pin.IN and label is not "CLK": SignalList.append(self)

    def value(self,setvalue=None):
        if DEBUG and setvalue!=None: # only debug if setting a value
            state="inactive"
            if (not self.active_low and setvalue) or (self.active_low and not setvalue): state="ACTIVE"
            print(self.label,"=",setvalue,"("+state+")")
        if setvalue!=None:
            self.pin.value(setvalue)
        else:
            return self.pin.value()

    def off(self):
        if self.active_low:
            self.value(1)
        else:
            self.value(0)

    def on(self):
        if self.active_low:
            self.value(0)
        else:
            self.value(1)
    def isactive(self):
        if self.active_low:
            return 1-self.value()
        else:
            return self.value()

# Setup timers and pins here

def off(verbose=True, invert=False, report=False):
##    databus.setasinput()
##    databusHIGH.setasinput()

    CLK.off()
    if verbose: print("CLK: OFF")
    signaln=0
    for s in SignalList:
        if report:
            if (s.value()==0 and s.active_low) or (s.value()==1 and s.active_low==False):
                print(s.label,": ON!")
        else:
            if invert:
                s.on()
            else:
                s.off()
                if verbose: print(signaln,s.label,": OFF")
            signaln+=1
    if verbose: print(signaln,"control signals switched off")

def test_signals(waittime=0.1,verbose=True,tick=False):
    #waittime is in seconds
    period = waittime*1000000
    loop_condition = True
    while loop_condition:
        for s in SignalList:
            if tick: CLK.off()
            s.on()
            if verbose: print(s.label,":ON")
            microwait(period)
            s.off()
            if tick: CLK.on()
            if verbose: print(s.label,":OFF")
            microwait(period)
        loop_condition= tick

def burnBIN(binfilename="test.bin"):
    f = open(binfilename,"rb")
    data = f.read()
    f.close

    PC = 0
    size=len(data)
    for byte in data:
        writeMEM(PC,byte)
        PC+=1
        print(hex(byte))
    print("Binary file",binfilename,"written, total bytes="+str(size))
        
def program(filename="test.asm"):
    off(verbose=False)
    try:
        with open(filename) as file:
            my_program = [line.rstrip() for line in file]
    except OSError:
        print("file not found!", filename)
        return
                
    PC = 0
    
    for line_num,asm_line in enumerate(my_program):
        printstr=hex4(PC)+": "#"{0:#0{1}x} : ".format(PC,6)
        if ";" in asm_line:
            asm_line=asm_line.split(";")[0]
        asm_line=asm_line.strip()
        
        machine_lang = asm(asm_line)
        if machine_lang==None:
            print("could not parse asm:",asm_line,"on line:",line_num)
            return
        #print(asm_line)
        for byte in machine_lang:
            if byte!=None:
                writeMEM(PC,byte)
                PC+=1
                printstr += hex2(byte)+" "#"{0:#0{1}x} ".format(byte,4) #hex(byte)+" "
                #print(byte,hex(byte),bin(byte),chr(byte))
        printstr+="; "+asm_line
        print(printstr)
    print("Program written, next PC position=",PC,"("+hex4(PC)+")")
    return

def hex2(num):
    return "{0:#0{1}x}".format(num,4)

def hex4(num):
    return "{0:#0{1}x}".format(num,6)

def run(period=0.0,verb=False):
    off(verbose=False)
    execute(None,wait=period,verbose=verb,realmemory=True,start=0,end=0,loop=False)

def executeINS(asm_line,wait=0.5,verbose=True):
    execute(asm_line,wait,verbose,realmemory=False)
            
def execute(asm_line,wait=0.5,verbose=True,realmemory=False,start=0,end=0,loop=False):

    PC = 0
    MAR = 0

    test_uart = False
    
    if realmemory==False:
        machine_lang = asm(asm_line)
        print(machine_lang)
        if machine_lang==None:
            print("could not parse asm")
            return
        opcode = machine_lang[PC]
        print("Opcode=",opcode)
    else:
        PC=start
        if test_uart:
            opcode = 19 # mov U,0x??
            setI(opcode)
        else:
            opcode = readMEM(PC)[0]

    CLK.off()
    # Skipping FETCH instruction for NOW
    #setI(machine_lang[0]) # set address

    #constants:
    I_REG = 1
    A_REG = 2
    U_REG = 3
    
    while True:
        
        for tick in range(0,8):
            Z = 0
            C = 1 # no carry
            INS = opcode

            uart_output = 0 # Debug flag for piping output to UART

            address = (Z<<12)|(C<<11)|(tick<<8)|INS
            control_byte0 = control0[address]
            control_byte1 = control1[address]
            control_byte2 = control2[address]

            MC_RESET = False
            #new_INS = False
            
            for s in range(0,24):
                signal_name = SignalList[s].label
                s_mask = s&7
                # 0 1 2 3 4 5 6 7
                # 8 9 A B C D E F
                
                if s<8:                
                    bit = 1 if control_byte0&(1<<s_mask) else 0
                elif s<16:
                    bit = 1 if control_byte1&(1<<s_mask) else 0
                else:
                    bit = 1 if control_byte2&(1<<s_mask) else 0

                override = False

##                if signal_name=="MARi" and bit==0:
##                    MAR=PC
##                    #print("Setting MAR to PC",MAR)
##                    if realmemory:
##                        writeMAR(PC)
##                        override=True
##
##                if signal_name=="PCinc" and bit==1:
##                    PC+=1
##                    #print("INC PC to:",PC)

                if signal_name=="Ii" and bit==0:
                    #print("loading new INS")
                    #Uout.on()
                    uart_output = I_REG
                    #new_INS = True
                
                if signal_name=="Ro" and bit==0 and realmemory==False:                
                    #print("Ro sending", machine_lang[MAR])
                    uart.writechar(machine_lang[MAR])
                    Uin.on()
                    override=True # Send char by UART instead of MEM
                    
                if not override:
                    SignalList[s].value(bit)
                    
                if verbose:
                    if (SignalList[s].active_low and bit==0) or (SignalList[s].active_low==False and bit==1):
##                        if signal_name=="T_HL" or signal_name=="T_IO":
##                            signal_value=1
##                            if SignalList[s].active_low:
##                                signal_value=0
##                            print(signal_name,"=",signal_value)
                        if verbose: print("PC="+hex4(PC),"MAR="+hex4(MAR),"tick="+str(tick),"Ireg="+str(INS),"Signal",signal_name,"active")
                if signal_name=="MC_RESET" and bit==1:
                    #off(verbose=False)
                    MC_RESET = True
                if signal_name=="HALT" and bit==1:
                    return

                if signal_name=="Uout" and bit==1:
                    uart_output = U_REG
                # DEBUG: pipe Ai to UART:
                if signal_name=="Ai" and bit==0:
                    #Uout.on()
                    #print("outputing Ai to UART")
                    uart_output = A_REG
                # end of signal for loop
            # tick for loop     
            I2 = 1 if INS&(1<<2) else 0
            I3 = 1 if INS&(1<<3) else 0
            a3_o0 = I3 ^ X.value() # XOR
            in0 = I2 ^ X.value() # XOR

            alu_addr = INS&(0b111) | (a3_o0)<<3
            #print("ALU_ADDR:",alu_addr)
            if uart_output: Uout.on()
            
            microwait(wait*1E6)
            CLK.on()
            microwait(wait*1E6)
            CLK.off()
            microwait(1E4)
            Uout.off()
            Uin.off()
            off(verbose=False)
            
            if uart_output:
                n = uart.any()
                if n==1:
                    char = uart.read()[0]
                    if uart_output==A_REG:
                        print("A reg:",char,hex(char),bin(char),chr(char))
                    elif uart_output==I_REG:
                        #print("I reg:",char,hex(char),bin(char),chr(char))
                        if realmemory:
                            if test_uart:
                                opcode=19 # mov U,0x??
                            else:
##                                microwait(1E5)
##                                opcode = readMEM(MAR)[0]
                                opcode = char
                            INS = opcode
                    elif uart_output==U_REG:
                        print("UART output =",char)
                    else:
                        print("uart_output not supported!",uart_output)
                else:
                    print(n,"is not 1!",uart.read())
            
            uart_output=0
            if MC_RESET==True:
                #print("MC_RESET is true")
                break
            
            if verbose: print("-"*20)
        if realmemory==False: return
        # while LOOP
    
def OpenControlFile(filename):
    f = open(filename, "rb")
    readarray = f.read()
    f.close()
    return readarray

def testUART(char=None):
    Uin.on() # clear RX_READY
    Uin.off() # switch off to allow RX_READY to be set
    uart.read() # clear buffer

    errors = [0]*8
    
    for c in range(0,256):
        if char==None:
            i = c
        else:
            i = char
            
        #print("Sending",i)
        uart.writechar(i)
        microwait(1E3)        
        
        Uin.on() # for this purpose puts out to bus
        Uout.on() # gets ready to TX back from databus
        microwait(1E3)
        CLK.on() # Uout is pulled high (active) on testing circuit
        microwait(1E3)
        CLK.off()
        Uin.off()
        Uout.off()
        
        microwait(1E3)
        n = uart.any()
        
        if n==1:
            c = uart.read()[0]
            if c==i:
                print(hex(i),": YES  :",bin(c))
            else:
                print(hex(i),": ERROR:",bin(c),"(expected:",bin(i),")")
                for bit in range(0,8):
                    bitshift = 1<<bit
                    if c&bitshift!=i&bitshift:
                        errors[bit]+=1
        if n==0:
            print("not received!")
        if n>1:
            print("Multiple chars:",uart.read())
    print(errors)

def writeT(value):
    # Writes to 299 in T register from low databus
    #T_IO.on() # T_IO = 0 (means INPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    #T_HL.on() # T_HL = 0 (LOW bus)

    uart.writechar(value&0xff)
    microwait(1E3)
    Uin.on()
    microwait(1E2)
    CLK.on()
    microwait(1E2)
    CLK.off()
    Uin.off()

    #T_IO.off()
    T_EN.off()
    #T_HL.off()

def writeTHIGH(value):
    # Writes to 299 in T register from HIGH databus
    #T_IO.on() # T_IO = 0 (means INPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    T_HL.on() # T_HL = 1 (HIGH bus)

    uart.writechar(value&0xff)
    microwait(1E5)
    Uin.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    Uin.off()
    
    #T_IO.off()
    T_EN.off()
    T_HL.off()

def readT():
    # Read from 299 in T register onto low databus
    T_IO.on() # T_IO = 1 (means OUTPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    #T_HL.on() # T_HL = 0 (LOW bus)

    MARi.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    MARi.off()

    T_IO.off()
    T_EN.off()
    #T_HL.off()
    
def readTHIGH():
    # Read from 299 in T register onto high databus
    T_IO.on() # T_IO = 1 (means OUTPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    T_HL.on() # T_HL = 1 (HIGH bus)

    MARi.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    MARi.off()

    T_IO.off()
    T_EN.off()
    T_HL.off()

def shr():
    X.on()
    writeT(0) # value doesn't matter
    X.off()
    readT()

def writeMAR(address):
    low = address & 0xFF
    high = (address>>8)&0xFF

    writeT(high)
    
    uart.writechar(low)
    microwait(1E3) # sending UART char

    T_IO.on() # Read from T onto HIGH
    T_EN.on()
    T_HL.on()
    
    Uin.on()
    MARi.on()
    microwait(1E3)
    CLK.on()
    microwait(1E3)
    CLK.off()
    Uin.off()
    MARi.off()
    T_IO.off()
    T_EN.off()
    T_HL.off()

def readMEM(address, verbose=False):
    writeMAR(address)
    Ro.on()
    Uout.on()

    #DEBUG:
    # Writes from 299 in T register from low databus
##    T_IO.on() # T_IO = 0 (means INPUT)
##    T_EN.on() # T_EN = 1 (ENABLE)
##    T_HL.on() # T_HL = 0 (LOW bus)

    microwait(1E2)
    CLK.on()
    microwait(1E2)
    CLK.off()
    microwait(1E3) # Uart output time
    Uout.off()
    Ro.off()

##    T_IO.off()
##    T_EN.off()
##    T_HL.off()
##    
##    ## Reads from T register into MARi low
##    readT()
    
    
    if uart.any()>0:
        chars = uart.read()
        if verbose:
            for c in chars:
                print(hex(c),int(c),chr(c))
        return chars
    elif verbose:
        print("nothing!")
        return None

def writeMEM(address, data):
    writeMAR(address)
    uart.writechar(data)
    Ri.on()
    Uin.on()
    microwait(1E3) # sending UART char
    CLK.on()
    microwait(1E2)
    CLK.off()
    microwait(1E2)
    Uin.off()
    Ri.off()

def setI(data):
    uart.writechar(data)
    Ii.on()
    Uin.on()
    microwait(1E3)
    CLK.on()
    CLK.off()
    Ii.off()
    Uin.off()
    
def testMEM(write=False,seed=69):
    import random
    random.seed(seed)
    if write==True:
        print("Writing")
        for a in range(0,0x10000):
            db = random.randint(0,256)
            writeMEM(a,db)
    print("Reading")
    random.seed(seed)
    mismatches = 0
    memory_map = 0x81
    
    for a in range(0,0x10000):
        db = random.randint(0,256)
        read = readMEM(a)
        
        if read==None:
            print("Nothing returned at address:",hex(a))
        elif len(read)>1:
            print("Multiple characters received at address:",hex(a))
        elif read[0]!=db and db!=256:
            if a>>8!=memory_map:
                print("Mismatch at address:",hex(a),read[0],"!=",db)
                mismatches+=1        
    print("Total errors:",mismatches)       
micros = pyb.Timer(2, prescaler=83, period=0x3fffffff)

CLK = Signal("CLK","Y3", Pin.OUT_PP, active_low = False)

Ai = Signal("Ai","Y4", Pin.OUT_PP, active_low=True)
ALUo = Signal("ALUo","Y5", Pin.OUT_PP, active_low=True)
Ii = Signal("Ii","Y6", Pin.OUT_PP, active_low=True)
PCo = Signal("PCo","Y7", Pin.OUT_PP, active_low=True)
PCinc = Signal("PCinc","Y8", Pin.OUT_PP, active_low=False)
MARi = Signal("MARi","X9", Pin.OUT_PP, active_low=True)
Ro = Signal("Ro","X10", Pin.OUT_PP, active_low=True)
MC_RESET = Signal("MC_RESET","X11", Pin.OUT_PP, active_low=False)

T_HL = Signal("T_HL","X12", Pin.OUT_PP, active_low=False)
T_IO = Signal("T_IO","X17", Pin.OUT_PP, active_low=False)
T_EN = Signal("T_EN","X18", Pin.OUT_PP, active_low=False)
Ri = Signal("Ri","X19", Pin.OUT_PP, active_low=False)
Fi = Signal("Fi","X20", Pin.OUT_PP, active_low=True)
SPdec = Signal("SPdec","X21", Pin.OUT_PP, active_low=False)
SPinc = Signal("SPinc","X22", Pin.OUT_PP, active_low=False)
Bi = Signal("Bi","X1", Pin.OUT_PP, active_low=True)

PCi = Signal("PCi","X2", Pin.OUT_PP, active_low=False)
Ao = Signal("Ao","X3", Pin.OUT_PP, active_low=True)
OUTen = Signal("OUTen","X4", Pin.OUT_PP, active_low=True)
INen = Signal("INen","X5", Pin.OUT_PP, active_low=True)
X = Signal("X","X6", Pin.OUT_PP, active_low=False)
Fo = Signal("Fo","X7", Pin.OUT_PP, active_low=True)
HALT = Signal("HALT","X8", Pin.OUT_PP, active_low=False)
SPo = Signal("SPo","Y9", Pin.OUT_PP, active_low=True)

# Bo is just included for convenience here - it is generated by the register module
# so remember to remove before adding that!

#Bo = Signal("Bo","Y10", Pin.OUT_PP, active_low=True)
Uin = Signal("Uin","Y11", Pin.OUT_PP, active_low=True) # Green - right and middle
Uout = Signal("Uout","Y12", Pin.OUT_PP, active_low=False) # Blue- left and top
#RX_READY = Pin("Y12", Pin.IN, Pin.PULL_DOWN)

from pyb import UART
uart = UART(6,38400) # https://docs.micropython.orrg/en/latest/library/pyb.UART.html?highlight=uart
# uart 6: TX = Y1, RX = Y2
# uart.write(chr(0xAA)) 
# or uart.write('A')
# or uart.writechar(c))
# or setDatabus(c)
   
off()
uart.read() # clear uart buffer
test_signals(waittime=0.05)
off(invert=True)
microwait(1E6)
off()
#mock_working()
print("Ready")
#test_signals(waittime=0.2, verbose=False,tick=True)

control0 = OpenControlFile("control_EEPROM0.txt")
control1 = OpenControlFile("control_EEPROM1.txt")
control2 = OpenControlFile("control_EEPROM2.txt") 
print("hello")
from assembler import asm
print(asm("MOV A,B"))

##print("imported assembler")
##execute("INC A")
