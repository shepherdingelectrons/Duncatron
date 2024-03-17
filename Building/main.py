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

def off(verbose=True, invert=False):
##    databus.setasinput()
##    databusHIGH.setasinput()

    CLK.off()
    if verbose: print("CLK: OFF")
    signaln=0
    for s in SignalList:
        if invert:
            s.on()
        else:
            s.off()
            if verbose: print(signaln,s.label,": OFF")
        signaln+=1
    if verbose: print(signaln,"control signals switched off")
        

def toggleCLK(setsignals=None):
   # SPEED
## Assumes clock is OFF to begin with
## speed is clock speed in Hz
    
    if CLK.value()!=0:
        print("Error: expect CLK to be low")

    period = 1E6/SPEED # clock period in microseconds
    
    if setsignals: # We have to hope the clock isn't too fast otherwise
    # we can't set all the signals in time before the 0--> transition!
        for s in setsignals:
            s.on()
        
    microwait(period/2)
    CLK.on()
    microwait(period/2)
    
    # Now turn everything off
    if setsignals: # Turn all signals off
        for s in setsignals:
            s.off()

    CLK.off()
    
    microwait(1000) # wait for clock to settle off
    microwait(period/2)

def writedata(data):
    uart.writechar(data&0xff)
    microwait(1000) # we have to wait for the micropython uart
    toggleCLK([RI,RXout])

def readdata():
    toggleCLK([RO,TXout])
    microwait(1000) # we have to wait for the micropython
    # uart code to catch up with the hardware...
    n = uart.any()
    if n==0:
        print("ERROR NO UART RECEIVED")
        return
    if n>1:
        print("warning, multiple values on RX line")
    cs = uart.read()[n-1] # get last character 
    print(chr(cs),cs,hex(cs))

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

def tick(ticktime=0.1):
    period = ticktime*1000000
    while True:
        CLK.on()
        microwait(period)
        CLK.off()
        microwait(period)

def mock_working(waittime=0.1):
    import random

    period = waittime *1000000
    probn = 7
    while True:
        for s in SignalList:
            rand = random.randint(0,probn)
            if rand==0:
                s.on()
        microwait(period)
        CLK.on()
        microwait(period)
        off(verbose=False)
        CLK.off()

def flash(signals):
    while True:
        for s in signals:
            s.on()
        microwait(200000)
            
        for s in signals:
            s.off()
        microwait(200000)

def execute(asm_line,wait=0.5,verbose=True):
    machine_lang = asm(asm_line)
    if machine_lang==None:
        print("could not parse asm")
        return
    opcode = machine_lang[0]
    print("Opcode=",opcode)
    for tick in range(0,8):
        CLK.off()
        Z = 0
        C = 1 # no carry
        INS = opcode

        address = (Z<<12)|(C<<11)|(tick<<8)|INS
        control_byte0 = control0[address]
        control_byte1 = control1[address]
        control_byte2 = control2[address]
        
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
        
            SignalList[s].value(bit)
            if verbose:
                if (SignalList[s].active_low and bit==0) or (SignalList[s].active_low==False and bit==1):
                    if signal_name!="T_HL" and signal_name!="T_IO":                    
                        print(tick,"Signal",signal_name,"active")
            if signal_name=="MC_RESET" and bit==1:
                off(verbose=False)
                return
        I2 = 1 if INS&(1<<2) else 0
        I3 = 1 if INS&(1<<3) else 0
        a3_o0 = I3 ^ X.value() # XOR
        in0 = I2 ^ X.value() # XOR

        alu_addr = INS&(0b111) | (a3_o0)<<3
        print("ALU_ADDR:",alu_addr)
        microwait(wait*1E6)
        CLK.on()
        microwait(wait*1E6)

def OpenControlFile(filename):
    f = open(filename, "rb")
    readarray = f.read()
    f.close()
    return readarray

def testUART():
    Uin.on() # clear RX_READY
    Uin.off() # switch off to allow RX_READY to be set
    uart.read() # clear buffer

    for i in range(0,256):
        print("Sending",i)
        uart.writechar(i)
        
        microwait(1E5)        
        
        Uin.on() # for this purpose puts out to bus
        Uout.on() # gets ready to TX back from databus
        microwait(1E4)
        CLK.on() # Uout is pulled high (active) on testing circuit
        microwait(1E5)
        CLK.off()
        Uin.off()
        Uout.off()
        
        microwait(1E4)
        n = uart.any()
        
        if n==1:
            c = uart.read()[0]
            print("Got:",c)
            if c!=i:
                print("ERROR mismatch:",i,c)
        if n==0:
            print("not received!")
        if n>1:
            print("Multiple chars:",uart.read())

def writeT(value):
    # Reads from 299 in T register from low databus
    T_IO.on() # T_IO = 0 (means INPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    T_HL.on() # T_HL = 0 (LOW bus)

    uart.writechar(value&0xff)
    microwait(1E5)
    Uin.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    Uin.off()

    T_IO.off()
    T_EN.off()
    T_HL.off()

def writeTHIGH(value):
    # Writes to 299 in T register from HIGH databus
    T_IO.on() # T_IO = 0 (means INPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    T_HL.off() # T_HL = 1 (HIGH bus)

    uart.writechar(value&0xff)
    microwait(1E5)
    Uin.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    Uin.off()
    
    T_IO.off()
    T_EN.off()
    T_HL.off()

def readT():
    # Read from 299 in T register onto low databus
    T_IO.off() # T_IO = 1 (means OUTPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    T_HL.on() # T_HL = 0 (LOW bus)

    MARi.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    MARi.off()

    T_IO.off()
    T_EN.off()
    T_HL.off()
    
def readTHIGH():
    # Read from 299 in T register onto high databus
    T_IO.off() # T_IO = 1 (means OUTPUT)
    T_EN.on() # T_EN = 1 (ENABLE)
    T_HL.off() # T_HL = 1 (HIGH bus)

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
    microwait(1E5)

    T_IO.off() # Read from T onto HIGH
    T_EN.on()
    T_HL.off()
    
    Uin.on()
    MARi.on()
    microwait(1E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    Uin.off()
    MARi.off()
    T_EN.off()

def readMEM(address):
    writeMAR(address)
    Ro.on()
    microwait(1E5)
    Uout.on() 
    microwait(1E6)
    CLK.on()
    microwait(1E5)
    CLK.off()
    microwait(1E5)
    Uout.off()
    Ro.off()
    
    if uart.any()>0:
        chars = uart.read()
        for c in chars:
            print(hex(c),int(c),chr(c))
    else:
        print("nothing!")

def writeMEM(address, data):
    writeMAR(address)
    uart.writechar(data)
    Ri.on()
    Uin.on()
    microwait(2E5)
    CLK.on()
    microwait(1E5)
    CLK.off()
    microwait(1E5)
    Uin.off()
    Ri.off()

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

T_HL = Signal("T_HL","X12", Pin.OUT_PP, active_low=True)
T_IO = Signal("T_IO","X17", Pin.OUT_PP, active_low=True)
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

Bo = Signal("Bo","Y10", Pin.OUT_PP, active_low=True)
Uin = Signal("Uin","Y11", Pin.OUT_PP, active_low=True)
Uout = Signal("Uout","Y12", Pin.OUT_PP, active_low=False)
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
test_signals()
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
