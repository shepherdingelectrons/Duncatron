import random

class signal():
    def __init__(self,Computer,signalname,activeLow=False,demux=False):
        self.name = signalname
        self.activeLow = activeLow
        self.value = self.off()
        self.controlword = None
        self.Computer = Computer

        self.Computer.signal_group.append(self) # Add an instance to the list
        
    def isactive(self,demux_index):
        if demux_index==None:
            if self.value==self.on():
                return 1
        else:
            # is the signal on INen or OUTen bank?
            ins = self.Computer.I_reg.value
            # i2 i1 o2 o1 o0 i0 x x
            if self.name=="INen":
                i2 = 1 if (1<<7)&ins else 0
                i1 = 1 if (1<<6)&ins else 0
                i0 = 1 if (1<<2)&ins else 0

                #if X.isactive(None):
                i0=self.Computer.X.value ^ i0# XOR
                    #i0=1-i0
                self.setControlWord((i2<<2)|(i1<<1)|i0)
 
            elif self.name=="OUTen":
                o2 = 1 if (1<<5)&ins else 0
                o1 = 1 if (1<<4)&ins else 0
                o0 = 1 if (1<<3)&ins else 0

                #if X.isactive(None):
                #    o0 = 1-o0
                o0 = self.Computer.X.value ^ o0 # XOR
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
    def __init__(self,Computer,name,IN=None,OUT=None,bit16=False): 
        self.databus = Computer.LOW_databus
        self.databusHI = Computer.HI_databus if bit16 else None
        self.Computer = Computer
        
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
            self.Computer.CPU.connect(self,sig,dm,action,clocklatch)

    def select_databus(self):
        if self.Computer.T_HL.value==0: # Choose target databus based on T_HL signal
            self.databus=self.Computer.LOW_databus
        else:
            self.databus=self.Computer.HI_databus
                
    def output(self):
        # Special case for T register
        if self.name=="T":
            if self.Computer.T_IO.value==1: # Means Transfer register set for output
                self.select_databus()
            else:
                return # Do nothing, return

        if self.databusHI!=None:
            self.databusHI.set(self.valueHI)
        self.databus.set(self.value&0xFF)
    
    def latch(self):
        # Special case for T register
        if self.name=="T":
            if self.Computer.T_IO.value==0: # Means Transfer register set for input
                self.select_databus()
                if self.Computer.X.value==1: # X is asserted during a T register load-->SHR
                    self.value = self.value>>1 # UNTESTED
                    return
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
    def __init__(self,Computer):        
        self.microcode_counter = 0
        self.connections=[]
        self.Computer = Computer# reference to parent Computer object
    
    def connect(self,obj,con_signal,demux,action,clocklatch=False):
        self.connections.append((obj,con_signal,demux,action,clocklatch))
        return(len(self.connections)-1)

    def handlesignals(self,latchcondition=False):
         for c in self.connections:
            obj,sig,dm,action,clocklatch = c # Object, signal, demux (or not)

            if sig.isactive(dm) and clocklatch==latchcondition: # A signal is active
                action()

    def handleoutputs(self):
        self.Computer.LOW_databus.updates=0 # Clear update counter
        self.Computer.HI_databus.updates=0

        self.handlesignals(latchcondition=False)                   

        if self.Computer.LOW_databus.updates==0:
            self.Computer.LOW_databus.floatbus()
            #print("Floating LOW bus...")
        if self.Computer.HI_databus.updates==0:
            self.Computer.HI_databus.floatbus()
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
        print("A=",self.Computer.A_reg.value,"B=",self.Computer.B_reg.value,"F=",self.Computer.F_reg.value,"PC=",hex(self.Computer.PC.valueHI<<8|self.Computer.PC.value),"MAR=",hex(self.Computer.MAR.valueHI<<8|self.Computer.MAR.value),"T=",self.Computer.T_reg.value,"I=",self.Computer.I_reg.value,\
              "r0=",self.Computer.r0.value,"r1=",self.Computer.r1.value,"r2=",self.Computer.r2.value,"r3=",self.Computer.r3.value,"r4=",self.Computer.r4.value,"r5=",self.Computer.r5.value,"U=",self.Computer.U_reg.value,"SP=",hex(self.Computer.SP.valueHI<<8|self.Computer.SP.value))
        SP_value=self.Computer.SP.valueHI<<8|self.Computer.SP.value
##        if SP_value>0:
##        for i in range(0xfffA,0xFFFF+1):
##            print("Stack["+str(i)+"]="+str(Memory[i]))

    def set_controls(self, verbose=False):
        # FLAGS: x x TX_SENDING RX_READY x N C Z
        # Z C m m m I I I I I I I I
        FLAGS = self.Computer.F_reg.value
        Z = 1 if FLAGS&1 else 0
        C = 1 if FLAGS&2 else 0
        
        address = (Z<<12)|(C<<11)|(self.microcode_counter<<8)|self.Computer.I_reg.value
        control_byte0 = control0[address] # control_EEPROM0
        control_byte1 = control1[address]
        control_byte2 = control2[address]

        if verbose: print("Addr=",address,"Microcode_counter=",self.microcode_counter,control_byte0,control_byte1,control_byte2)
        for s in range(0,len(self.Computer.signal_group)):
            s_mask = s&7
            # 0 1 2 3 4 5 6 7
            # 8 9 A B C D E F
            
            if s<8:                
                bit = 1 if control_byte0&(1<<s_mask) else 0
            elif s<16:
                bit = 1 if control_byte1&(1<<s_mask) else 0
            else:
                bit = 1 if control_byte2&(1<<s_mask) else 0
                
            self.Computer.signal_group[s].value = bit
            if bit==self.Computer.signal_group[s].on() and verbose:
                print("Signal",self.Computer.signal_group[s].name,"active")
        
    
    def compute(self,verbose=False):
        # Look up control signal states based on Z,C,microcode counter and set

        if verbose: print("*"*50)
        
        self.set_controls(verbose)

        self.Computer.ALU.ALUcalc() # What is the ALU value before clock pulse? This will be used output
        # onto the bus and to set the FLAGS correctly.

        # Check if new set of controls has MC_reset set, if so instantly reset
        # microcode counter and get and set next control set (simulates what
        # would happen in the hardware)

        if self.Computer.MC_reset.isactive(None):
            if verbose: print("MC_reset active")
            
            if self.Computer.MC_RESET_terminate==False:
                self.microcode_counter = 0
                self.set_controls(verbose) # get next signal set
            else:
                self.microcode_counter = -1 # ensure next counter value will be 0
    
        if not self.Computer.HALT.isactive(None):
            self.clockpulse() # Do the thing
        else:
            return

        # Increment microcode clock and wrap around at 0-7
        self.microcode_counter =(self.microcode_counter+1)&7
        
        if verbose: self.displaystate()

        if self.Computer.console!=None:
            if self.Computer.U_reg.value!=-1: # Bit of a hack - means we just loaded a value into U reg for TX
                if verbose: print(chr(self.Computer.U_reg.value), end='')
                #self.Computer.console.printToConsole(self.Computer.U_reg.value)
                #self.Computer.console.readQueue.append(self.Computer.U_reg.value)
                self.Computer.readQueue.append(self.Computer.U_reg.value) 
                self.Computer.U_reg.value=-1

        if verbose:# and self.microcode_counter==2:
            print("Loaded instruction:",hex(self.Computer.I_reg.value))#asm.lookupASM[self.I_reg.value])
            self.analyse_microcode(0,1,self.Computer.I_reg.value)
            input(">") # Wait for keypress between clock cycles

    def analyse_microcode(self,Z,C,instruction):
        #address = (Z<<12)|(C<<11)|(self.microcode_counter<<8)|self.Computer.I_reg.value
        for i in range(0,8):
            address = Z<<12|C<<11|i<<8|(instruction&0xFF)
            control_byte0 = control0[address]
            control_byte1 = control1[address]
            control_byte2 = control2[address]

            signals_active = []
            for s in range(0,len(self.Computer.signal_group)):
                s_mask = s&7
                # 0 1 2 3 4 5 6 7
                # 8 9 A B C D E F
                
                if s<8:                
                    bit = 1 if control_byte0&(1<<s_mask) else 0
                elif s<16:
                    bit = 1 if control_byte1&(1<<s_mask) else 0
                else:
                    bit = 1 if control_byte2&(1<<s_mask) else 0
                    
                self.Computer.signal_group[s].value = bit
                if bit==self.Computer.signal_group[s].on():
                    signals_active.append(self.Computer.signal_group[s].name)
            print(hex(instruction),":",i,":",signals_active)
class ArithmeticLogicUnit():
    def __init__(self,Computer):
        self.ALU_data = 0
        self.ALU_carry = 0
        self.Computer = Computer # reference to parent Computer object
        
    def not_8bit(self,a):
        result = 0
        for i in range(0,8):
            bit = 0 if (1<<i)&a else (1<<i)
            result |= bit
        return result

    def nor_8bit(self,a,b):
        result = 0
        for i in range(0,8):
            bit = 0 if (((1<<i)&a) | ((1<<i)&b)) else (1<<i)
            result |= bit
            #result |= ~(((1<<i)&a) | ((1<<i)&b))
        return result

    def or_8bit(self,a,b):
        result = 0
        for i in range(0,8):
            result |= ((1<<i)&a) | ((1<<i)&b)
        return result

    def xor_8bit(self,a,b):
        result = 0
        for i in range(0,8):
            result |= ((1<<i)&a) ^ ((1<<i)&b)
        #print(a,b,result)
        return result

    def nand_8bit(self,a,b):
        result = 0
        for i in range(0,8):
            bit = 0 if ( ((1<<i)&a) & ((1<<i)&b)) else 1
            result |= bit
            #result |=~( ((1<<i)&a) & ((1<<i)&b))
        return result

    def and_8bit(self,a,b):
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

    def ALUFUNC(self,alu,a,b,carry):
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
            return (self.not_8bit(a),1)
        elif alu==8: # SHL A
            return (a<<1,(a&128)==0)
        elif alu==9:
            return (self.xor_8bit(a,b),1)
        elif alu==10:
            return (self.nand_8bit(a,b),1)
        elif alu==11:
            return (self.or_8bit(a,b),1)
        elif alu==12:
            return (a+1,(a+1)<256)
        elif alu==13:
            return (self.and_8bit(a,b),1)
        elif alu==14:
            return (self.nor_8bit(a,b),1)
    ##    elif alu==15:
    ##        return (0,1)
        elif alu==15: # RCL A
            return ((a<<1)|(carry),(a&128)==0)

     # old   
    #ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B","SUBC A,B"
            #,"CMPC A,B","NOT A","OR A,B","NOR A,B","NAND A,B","XOR A,B","INC A",
            # "AND A,B", "SHL A", "RCL A"]
    def setFlags(self):
        value = self.ALU_data
        newcarry = self.ALU_carry # might be 0 or 1
        Neg = 0
        Zero = 0
        
        if self.ALU_carry==False: # might be true or false
            newcarry=0
        elif self.ALU_carry==True:
            newcarry=1
        
        if value>255:
            value = value & 0xff
        if value&(1<<7):
            Neg=1
        if value==0:
            Zero=1
        self.Computer.F_reg.value=(self.Computer.F_reg.value&0b11111000)|(Neg<<2)|(newcarry<<1)|Zero

        # X X RX_READY SENDING X N C Z
        if not self.Computer.T_IO.isactive(None): # The relationship between Fi direction and T_IO was inverted due to a PCB error... now NOT isactive
            highflags = self.Computer.F_reg.value & 0b11110000
            value=self.Computer.F_reg.databus.value # take Flag register directly from low databus rather than ALU
            self.Computer.F_reg.value=highflags | (value&0b1111)
            #print("F from databus",value)
        

    def ALUcalc(self):
        #global ALU_data, ALU_carry
        
        alu_func = self.Computer.I_reg.value & 0b1111
        a3 = 1 if alu_func&(1<<3) else 0
        #if X.isactive(None):
        #    a3=1-a3
        a3 = self.Computer.X.value ^ a3 # XOR
        
        alu_func = (a3<<3) | (alu_func&0b0111)

        # Use alu_func to set function
        # FLAGS: x x TX_SENDING RX_READY x N C Z
        carry=1 if self.Computer.F_reg.value&2 else 0
        
        Neg=0
        Zero=0
        # invert carry for arithmetic.  Correctly inverted carry is returned
        value,carry = self.ALUFUNC(alu_func, self.Computer.A_reg.value,self.Computer.B_reg.value,1-carry)
        self.ALU_data = value&0xFF
        self.ALU_carry = carry

    def ALUout(self):
        self.Computer.LOW_databus.set(self.ALU_data)

    
class Computer():
    # Class that brings together the signals, databuses, ALU and memory
    def __init__(self):
        self.signal_group = [] # This gets populated in sequential order as signals are
        # defined, therefore the signal definition order is important and needs to
        # match the order defined in 'define_instructions.py', as well as matching
        # whether the signal is an active low or not.

        # A,B, ALU, Flags and registers r0-r5
        self.Ai = signal(self,"Ai",activeLow=True)
        self.ALUo = signal(self,"ALUo",activeLow=True)
        self.Ii = signal(self,"Ii",activeLow=True)
        self.PCo = signal(self,"PCo",activeLow=True)
        self.PCinc = signal(self,"PCinc")
        self.MARi = signal(self,"MARi",activeLow=True)
        self.Ro = signal(self,"Ro",activeLow=True)
        self.MC_reset = signal(self,"MC_reset")

        self.T_HL = signal(self,"T_HL") # need to check polarity of these signals. For now assume H=1, L=0
        self.T_IO = signal(self,"T_IO") # need to check polarity of these signals. For now assume I=1, O=0
        self.T_EN = signal(self,"T_EN") # need to check polarity of these signals. For now assume enable = 1
        self.Ri = signal(self,"Ri")
        self.Fi = signal(self,"Fi",activeLow=True) # T_IO flag is used to control flag in direction (from ALU or databus)
        self.SPdec = signal(self,"SPdec")
        self.SPinc = signal(self,"SPinc")
        self.Bi = signal(self,"Bi",activeLow=True)

        self.PCi = signal(self,"PCi")
        self.Ao = signal(self,"Ao",activeLow=True)
        self.OUTen = signal(self,"OUTen",activeLow=True,demux=True)
        self.INen = signal(self,"INen",activeLow=True,demux=True)
        self.X = signal(self,"X")
        self.Fo = signal(self,"Fo",activeLow=True)
        self.HALT = signal(self,"HALT")
        self.SPo = signal(self,"SPo",activeLow=True)

        self.LOW_databus = databus("LOW8",floating=lambda : self.X.value)
        self.HI_databus = databus("HI8",floating=lambda : 0x80) # 0x88--> 0x80 Zero page
        self.CPU = ControlLogic(self) # Pass on reference to parent Computer object
        self.ALU = ArithmeticLogicUnit(self)
        self.console = None
        self.readQueue = []

        #Registers need CPU to exist at this point for CPU.connect in register __init__

        self.A_reg = register(self,name="A", IN=(self.Ai,None),OUT=(self.Ao,None))
        self.B_reg = register(self,name="B", IN=(self.Bi,None),OUT=(self.OUTen,1))
        self.F_reg = register(self,name="F", IN=None,OUT=(self.Fo,None))
        self.PC = register(self,name="PC",IN=(self.PCi,None),OUT=(self.PCo,None),bit16=True)
        self.MAR = register(self,name="MAR",IN=(self.MARi,None),OUT=None,bit16=True)
        self.SP = register(self,name="SP",IN=None,OUT=(self.SPo,None),bit16=True)
        self.T_reg = register(self,name="T",IN=(self.T_EN,None),OUT=(self.T_EN,None))
        self.I_reg = register(self,name="I",IN=(self.Ii,None))

        self.r0 = register(self,name="r0",IN=(self.INen,2),OUT=(self.OUTen,2))
        self.r1 = register(self,name="r1",IN=(self.INen,3),OUT=(self.OUTen,3))
        self.r2 = register(self,name="r2",IN=(self.INen,4),OUT=(self.OUTen,4))
        self.r3 = register(self,name="r3",IN=(self.INen,5),OUT=(self.OUTen,5))
        self.r4 = register(self,name="r4",IN=(self.INen,6),OUT=(self.OUTen,6))
        self.r5 = register(self,name="r5",IN=(self.INen,7),OUT=(self.OUTen,7))

        self.U_reg = register(self,name="U",IN=(self.INen,0))#,OUT=(INen,1))

        self.Memory = bytearray(2**16)
        
        # obj,sig,dm,action,clocklatch 
        self.CPU.connect(self.PC,self.PCinc,None,self.PC.increment,clocklatch=True)
        self.CPU.connect(None,self.Ro,None,self.RAMout)
        self.CPU.connect(None,self.Ri,None,self.RAMin,clocklatch=True)

        self.CPU.connect(None,self.ALUo,None,self.ALU.ALUout)
        self.CPU.connect(None,self.Fi,None,self.ALU.setFlags,clocklatch=True)

        self.CPU.connect(self.SP,self.SPinc,None,self.SP.increment,clocklatch=True)
        self.CPU.connect(self.SP,self.SPdec,None,self.SP.decrement,clocklatch=True)

        self.CPU.connect(None,self.OUTen,0,self.clear_int,clocklatch=True)

        self.CPU.connect(self.U_reg,self.INen,1,self.UART_out) # Get UART received byte

        self.MC_RESET_terminate = True #
        # False = Old behaviour, MC_RESET is the only microcode run and
        # True = New behaviour, MC_RESET is ALWAYS asserted on the last instruction
        #       microcode and therefore clocks the INT logic it is de-asserted
        self.reset() # Starting positions

    def write(self,bytechar):
        # char should be a bytearray for compatibility with serial port objects
        if len(bytechar)>1:
            print("ERROR: bytearray to CPU write function should be a single character")
        char = bytechar[0]
        UART_RX = char &0xFF
        self.U_reg.valueHI = UART_RX # Use U_reg.valueHI for RX
        self.F_reg.value|=(1<<4) # Set RX_READY

    def read(self):
        readChars = bytearray(self.readQueue)
        self.readQueue = []
        return readChars
        
    def connectConsole(self,console):
        self.console = console
        if console.Computer == None:  # If console isn't connected, connect
            self.console.connectCPU(self)

    def RAMout(self):
        addr = (self.MAR.valueHI<<8) | self.MAR.value
        value = self.Memory[addr]
        self.LOW_databus.set(value)

    def RAMin(self):
        addr = (self.MAR.valueHI<<8) | self.MAR.value
        self.Memory[addr] = self.LOW_databus.value

    def randomiseRAM(self,start,end): # To simulate random values in RAM at startup and to help uncover bugs that otherwise assume RAM is always zero
        for m in range(start,end):
            self.Memory[m]=random.randint(0,255)

    def clear_int(self):
        print("Interrupt signal cleared")

    def UART_out(self):
        self.U_reg.databus.set(self.U_reg.valueHI&0xFF)  # If we put values here, they will go onto databus
        self.F_reg.value &= 0b11101111 # clear RX_READY flag

    def reset(self,clear_memory=True):    
        self.ALU.ALU_data = 0
        self.ALU.ALU_carry = 1

        self.A_reg.value=0
        self.B_reg.value=0

        self.PC.value=0
        self.PC.valueHI=0x00

        self.SP.value=0
        self.SP.valueHI=0

        self.U_reg.value=-1

        self.F_reg.value = (self.ALU.ALU_carry<<1)
        self.I_reg.value = 0x0

        for signal in self.signal_group:
            signal.unset()
        
        if clear_memory:
            for a in range(len(self.Memory)):
                self.Memory[a]=0

def OpenControlFile(filename):
    f = open(filename, "rb")
    readarray = f.read()
    f.close()
    return readarray

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

