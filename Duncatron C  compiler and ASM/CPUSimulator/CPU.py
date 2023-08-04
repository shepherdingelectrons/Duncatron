# CPU

class signal():
    def __init__(self,signalname,activeLow=False,demux=False):
        self.name = signalname
        self.activeLow = activeLow
        self.value = self.off()
        self.controlword = None

        signal_group.append(self) # Add an instance to the list
        
    def isactive(self,demux_index):
        if demux_index==None:
            if self.value==self.on():
                return 1
        else:
            # is the signal on INen or OUTen bank?
            ins = I_reg.value
            # i2 i1 o2 o1 o0 i0 x x
            if self.name=="INen":
                i2 = 1 if (1<<7)&ins else 0
                i1 = 1 if (1<<6)&ins else 0
                i0 = 1 if (1<<2)&ins else 0

                if X.isactive(None):
                    i0=1-i0
                self.setControlWord((i2<<2)|(i1<<1)|i0)
 
            elif self.name=="OUTen":
                o2 = 1 if (1<<5)&ins else 0
                o1 = 1 if (1<<4)&ins else 0
                o0 = 1 if (1<<3)&ins else 0

                if X.isactive(None):
                    o0 = 1-o0
                self.setControlWord((o2<<2)|(o1<<1)|o0)

            if self.value==self.on() and self.controlword == demux_index:
                return 1

        return 0
    
    def on(self):
        return 0 if self.activeLow else 1 # Turn on
    def off(self):
        return 1 if self.activeLow else 0 # Turn off
        
    def set(self): 
        self.value = self.on()
    def unset(self):
        self.value = self.off()
        
    def setControlWord(self,word):
        self.controlword = word # 0b000 - 0b111

class databus():
    def __init__(self,busname,floating=0):
        self.name = busname
        self.value = 0
        self.updates = 0
        self.floating = floating

    def floatbus(self):
        self.value=self.floating()
        
    def set(self,value):
        if self.updates==0:
            self.value=value
        else:
            print("ERROR: More than one device attempting to output onto bus:",self.name)
        self.updates+=1
        
    
class register():
    def __init__(self,name,IN=None,OUT=None,bit16=False): 
        self.databus=LOW_databus
        self.databusHI=HI_databus if bit16 else None
        
        self.name=name
        self.value = 0
        self.valueHI = 0
        self.IN=IN
        self.OUT=OUT

        self.CPU_connect(IN,self.latch,clocklatch=True)
        self.CPU_connect(OUT,self.output)
                
    def CPU_connect(self,sig,action,clocklatch=False):
        if sig!=None:
            sig, dm = sig
            CPU.connect(self,sig,dm,action,clocklatch)

    def select_databus(self):
        if T_HL.value==0: # Choose target databus based on T_HL signal
            self.databus=LOW_databus
        else:
            self.databus=HI_databus
                
    def output(self):
        # Special case for T register
        if self.name=="T":
            if T_IO.value==1: # Means Transfer register set for output
                self.select_databus()
            else:
                return # Do nothing, return

        if self.databusHI!=None:
            self.databusHI.set(self.valueHI)
        self.databus.set(self.value&0xFF)
    
    def latch(self):
        # Special case for T register
        if self.name=="T":
            if T_IO.value==0: # Means Transfer register set for input
                self.select_databus()
            else:
                return # Do nothing, return
            
        self.value = self.databus.value & 0xFF
        if self.databusHI!=None:
            self.valueHI = self.databusHI.value

    def increment(self):
        self.value += 1
        if self.value>255:
            if self.databusHI!=None:
                self.valueHI+=1
                self.valueHI = self.valueHI & 255
            self.value=0
            
    def decrement(self):
        self.value -= 1
        if self.value<0:
            if self.databusHI!=None:
                self.valueHI-=1
                self.valueHI = self.valueHI & 255
            self.value=255

class ControlLogic():
    def __init__(self):        
        self.microcode_counter = 0
        self.connections=[]
    
    def connect(self,obj,con_signal,demux,action,clocklatch=False):
        self.connections.append((obj,con_signal,demux,action,clocklatch))
        return(len(self.connections)-1)

    def handlesignals(self,latchcondition=False):
         for c in self.connections:
            obj,sig,dm,action,clocklatch = c # Object, signal, demux (or not)

            if sig.isactive(dm) and clocklatch==latchcondition: # A signal is active
                action()

    def handleoutputs(self):
        LOW_databus.updates=0 # Clear update counter
        HI_databus.updates=0

        self.handlesignals(latchcondition=False)                   

        if LOW_databus.updates==0:
            LOW_databus.floatbus()
            #print("Floating LOW bus...")
        if HI_databus.updates==0:
            HI_databus.floatbus()
            #print("Floating HI bus...")

    def clockpulse(self):
        
        # (0) set outputs correctly
        self.handleoutputs()
        
        # (1) Latch inputs
        self.handlesignals(latchcondition=True)
                
        # (2) Update databus to reflect outputs, after safely latching the inputs
        # This is more for asthetics and displaying the contents of the bus rather than
        # asthetics
        #self.handleoutputs()

        # Clear control signals
        #self.clearcontrolsignals()
        
        

    def clearcontrolsignals(self):
        for c in self.connections:
            obj,sig,dm,action,clocklatch = c # Object, signal, demux (or not),action,clocklatch
            sig.unset()

        X.unset()
            
    def displaystate(self):
        print("A=",A_reg.value,"B=",B_reg.value,"F=",F_reg.value,"PC=",hex(PC.valueHI<<8|PC.value),"MAR=",hex(MAR.valueHI<<8|MAR.value),"T=",T_reg.value,"I=",I_reg.value,\
              "r0=",r0.value,"r1=",r1.value,"r2=",r2.value,"r3=",r3.value,"r4=",r4.value,"r5=",r5.value,"U=",U_reg.value,"SP=",hex(SP.valueHI<<8|SP.value))
        SP_value=SP.valueHI<<8|SP.value
##        if SP_value>0:
##        for i in range(0xfffA,0xFFFF+1):
##            print("Stack["+str(i)+"]="+str(Memory[i]))

    def set_controls(self, verbose=False):
        # FLAGS: x x RX_READY TX_SENDING x N C Z
        # Z C m m m I I I I I I I I
        FLAGS = F_reg.value
        Z = 1 if FLAGS&1 else 0
        C = 1 if FLAGS&2 else 0
        
        address = (Z<<12)|(C<<11)|(self.microcode_counter<<8)|I_reg.value
        control_byte0 = control0[address] # control_EEPROM0
        control_byte1 = control1[address]
        control_byte2 = control2[address]

        if verbose: print("Addr=",address,"Microcode_counter=",self.microcode_counter,control_byte0,control_byte1,control_byte2)
        for s in range(0,len(signal_group)):
            s_mask = s&7
            # 0 1 2 3 4 5 6 7
            # 8 9 A B C D E F
            
            if s<8:                
                bit = 1 if control_byte0&(1<<s_mask) else 0
            elif s<16:
                bit = 1 if control_byte1&(1<<s_mask) else 0
            else:
                bit = 1 if control_byte2&(1<<s_mask) else 0
                
            signal_group[s].value = bit
            if bit==signal_group[s].on() and verbose:
                print("Signal",signal_group[s].name,"active")
        
    
    def compute(self,verbose=False):
        # Look up control signal states based on Z,C,microcode counter and set

        if verbose: print("*"*50)
        
        self.set_controls(verbose)

        ALUcalc() # What is the ALU value before clock pulse? This will be used output
        # onto the bus and to set the FLAGS correctly.

        # Check if new set of controls has MC_reset set, if so instantly reset
        # microcode counter and get and set next control set (simulates what
        # would happen in the hardware)
        if MC_reset.isactive(None):
            if verbose: print("MC_reset active")
            self.microcode_counter = 0
            self.set_controls(verbose) # get next signal set

        if not HALT.isactive(None):
            self.clockpulse() # Do the thing
        else:
            return
        
        # Increment microcode clock and wrap around at 0-7
        self.microcode_counter =(self.microcode_counter+1)&7
        
        if verbose: self.displaystate()

def RAMout():
    addr = (MAR.valueHI<<8) | MAR.value
    value = Memory[addr]
    LOW_databus.set(value)

def RAMin():
    addr = (MAR.valueHI<<8) | MAR.value
    Memory[addr] = LOW_databus.value

def not_8bit(a):
    result = 0
    for i in range(0,8):
        bit = 0 if (1<<i)&a else (1<<i)
        result |= bit
    return result

def nor_8bit(a,b):
    result = 0
    for i in range(0,8):
        bit = 0 if (((1<<i)&a) | ((1<<i)&b)) else (1<<i)
        result |= bit
        #result |= ~(((1<<i)&a) | ((1<<i)&b))
    return result

def or_8bit(a,b):
    result = 0
    for i in range(0,8):
        result |= ((1<<i)&a) | ((1<<i)&b)
    return result

def xor_8bit(a,b):
    result = 0
    for i in range(0,8):
        result |= ((1<<i)&a) ^ ((1<<i)&b)
    #print(a,b,result)
    return result

def nand_8bit(a,b):
    result = 0
    for i in range(0,8):
        bit = 0 if ( ((1<<i)&a) & ((1<<i)&b)) else 1
        result |= bit
        #result |=~( ((1<<i)&a) & ((1<<i)&b))
    return result

def and_8bit(a,b):
    result = 0
    for i in range(0,8):
        result |= ((1<<i)&a) & ((1<<i)&b)
    return result

# old:
# #ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B",
# "SUBC A,B","CMPC A,B","NOT A","XOR A,B","NOR A,B","NAND A,B","OR A,B",
# "INC A","AND A,B", "SHL A", "CLR A"]

# NEW:
# ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B",
# "SUBC A,B","CMPC A,B","NOT A","SHL A","XOR A,B","NAND A,B","OR A,B",
# "INC A","AND A,B", "NOR A,B", "RCL A"]

def ALUFUNC(alu,a,b,carry):
    if alu==0: #add a,b
        return (a+b,(a+b)<256)
    elif alu==1: #sub a,b
        return (a-b, a-b<0) # a<b = a-b<0
    elif alu==2: # cmp a,b
        return (a-b, a-b<0)
    elif alu==3: # dec a
        return (a-1,a-1<0) 
    elif alu==4: # addc a,b
        return (a+b+carry,(a+b+carry)<256)
    elif alu==5: # subc a,b
        return (a-b-(1-carry),(a-b-(1-carry))<0) # or a-b-carry?
    elif alu==6: # cmpc a,b
        return (a-b-(1-carry),(a-b-(1-carry))<0) # or a-b-carry?
    elif alu==7: # NOT
        return (not_8bit(a),1)
    elif alu==8: # SHL A
        return (a<<1,(a&128)==0)
    elif alu==9:
        return (xor_8bit(a,b),1)
    elif alu==10:
        return (nand_8bit(a,b),1)
    elif alu==11:
        return (or_8bit(a,b),1)
    elif alu==12:
        return (a+1,(a+1)<256)
    elif alu==13:
        return (and_8bit(a,b),1)
    elif alu==14:
        return (nor_8bit(a,b),1)
##    elif alu==15:
##        return (0,1)
    elif alu==15: # RCL A
        return ((a<<1)|(carry),(a&128)==0)

 # old   
#ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B","SUBC A,B"
        #,"CMPC A,B","NOT A","OR A,B","NOR A,B","NAND A,B","XOR A,B","INC A",
        # "AND A,B", "SHL A", "RCL A"]
def setFlags():
    value = ALU_data
    newcarry=ALU_carry # might be 0 or 1
    Neg = 0
    Zero = 0
    
    if ALU_carry==False: # might be true or false
        newcarry=0
    elif ALU_carry==True:
        newcarry=1
    
    if value>255:
        value = value & 0xff
    if value&(1<<7):
        Neg=1
    if value==0:
        Zero=1
    F_reg.value=(F_reg.value&0b11111000)|(Neg<<2)|(newcarry<<1)|Zero

    # X X RX_READY SENDING X N C Z
    if T_IO.isactive(None):
        highflags = F_reg.value & 0b11110000
        value=F_reg.databus.value # take Flag register directly from low databus rather than ALU
        F_reg.value=highflags | (value&0b1111)
        #print("F from databus",value)
    

def ALUcalc():
    global ALU_data, ALU_carry
    
    alu_func = I_reg.value & 0b1111
    a3 = 1 if alu_func&(1<<3) else 0
    if X.isactive(None):
        a3=1-a3
    
    alu_func = (a3<<3) | (alu_func&0b0111)

    # Use alu_func to set function
    # FLAGS: x x RX_READY TX_SENDING x N C Z
    carry=1 if F_reg.value&2 else 0
    
    Neg=0
    Zero=0
    # invert carry for arithmetic.  Correctly inverted carry is returned
    value,carry = ALUFUNC(alu_func, A_reg.value,B_reg.value,1-carry)
    ALU_data = value&0xFF
    ALU_carry = carry

def ALUout():
    LOW_databus.set(ALU_data)
    
def clear_int():
    print("Interrupt signal cleared")

def UART_out():
    U_reg.databus.set(U_reg.valueHI&0xFF)  # If we put values here, they will go onto databus
    F_reg.value &= 0b11011111 # clear RX_READY flag

def reset(clear_memory=True):    
    ALU_data = 0
    ALU_carry = 1

    A_reg.value=0
    B_reg.value=0

    PC.value=0
    PC.valueHI=0x00

    SP.value=0
    SP.valueHI=0

    U_reg.value=-1

    F_reg.value = (ALU_carry<<1)
    I_reg.value = 0x0

    for signal in signal_group:
        signal.unset()
    
    if clear_memory:
        for a in range(len(Memory)):
            Memory[a]=0

def OpenControlFile(filename):
    f = open(filename, "rb")
    readarray = f.read()
    f.close()
    return readarray

signal_group = [] # This gets populated in sequential order as signals are
# defined, therefore the signal definition order is important and needs to
# match the order defined in 'define_instructions.py', as well as matching
# whether the signal is an active low or not.

# A,B, ALU, Flags and registers r0-r5
Ai = signal("Ai",activeLow=True)
ALUo = signal("ALUo",activeLow=True)
Ii = signal("Ii",activeLow=True)
PCo = signal("PCo",activeLow=True)
PCinc = signal("PCinc")
MARi = signal("MARi")
Ro = signal("Ro")
MC_reset = signal("MC_reset")

T_HL = signal("T_HL") # need to check polarity of these signals. For now assume H=1, L=0
T_IO = signal("T_IO") # need to check polarity of these signals. For now assume I=1, O=0
T_EN = signal("T_EN") # need to check polarity of these signals. For now assume enable = 1
Ri = signal("Ri")
Fi = signal("Fi",activeLow=True) # T_IO flag is used to control flag in direction (from ALU or databus)
SPdec = signal("SPdec")
SPinc = signal("SPinc")
Bi = signal("Bi",activeLow=True)

PCi = signal("PCi")
Ao = signal("Ao",activeLow=True)
OUTen = signal("OUTen",activeLow=True,demux=True)
INen = signal("INen",activeLow=True,demux=True)
X = signal("X",activeLow=True)
Fo = signal("Fo",activeLow=True)
HALT = signal("HALT")
SPo = signal("SPo",activeLow=True)

LOW_databus = databus("LOW8",floating=lambda : X.value)
HI_databus = databus("HI8",floating=lambda : 0x88) # Zero page

CPU = ControlLogic()

A_reg = register(name="A", IN=(Ai,None),OUT=(Ao,None))
B_reg = register(name="B", IN=(Bi,None),OUT=(OUTen,1))
F_reg = register(name="F", IN=None,OUT=(Fo,None))
PC = register(name="PC",IN=(PCi,None),OUT=(PCo,None),bit16=True)
MAR = register(name="MAR",IN=(MARi,None),OUT=None,bit16=True)
SP = register(name="SP",IN=None,OUT=(SPo,None),bit16=True)
T_reg = register(name="T",IN=(T_EN,None),OUT=(T_EN,None))
I_reg = register(name="I",IN=(Ii,None))

r0 = register(name="r0",IN=(INen,2),OUT=(OUTen,2))
r1 = register(name="r1",IN=(INen,3),OUT=(OUTen,3))
r2 = register(name="r2",IN=(INen,4),OUT=(OUTen,4))
r3 = register(name="r3",IN=(INen,5),OUT=(OUTen,5))
r4 = register(name="r4",IN=(INen,6),OUT=(OUTen,6))
r5 = register(name="r5",IN=(INen,7),OUT=(OUTen,7))

U_reg = register(name="U",IN=(INen,0)) #,OUT=(INen,1)

Memory = bytearray(2**16)

# obj,sig,dm,action,clocklatch 
CPU.connect(PC,PCinc,None,PC.increment,clocklatch=True)
CPU.connect(None,Ro,None,RAMout)
CPU.connect(None,Ri,None,RAMin,clocklatch=True)

CPU.connect(None,ALUo,None,ALUout)
CPU.connect(None,Fi,None,setFlags,clocklatch=True)

CPU.connect(SP,SPinc,None,SP.increment,clocklatch=True)
CPU.connect(SP,SPdec,None,SP.decrement,clocklatch=True)

CPU.connect(None, OUTen,0,clear_int,clocklatch=True)

CPU.connect(U_reg,INen,1,UART_out) # Get UART received byte

reset() # Starting positions 

if __name__=="__main__":
    control0 = OpenControlFile("control_EEPROM0.txt")
    control1 = OpenControlFile("control_EEPROM1.txt")
    control2 = OpenControlFile("control_EEPROM2.txt")  
    #from control_EEPROM0 import control0
    #from control_EEPROM1 import control1
    #from control_EEPROM2 import control2
else:
    control0 = OpenControlFile(".\CPUSimulator\control_EEPROM0.txt")
    control1 = OpenControlFile(".\CPUSimulator\control_EEPROM1.txt")
    control2 = OpenControlFile(".\CPUSimulator\control_EEPROM2.txt")
    #from .control_EEPROM0 import control0
    #from .control_EEPROM1 import control1
    #from .control_EEPROM2 import control2

