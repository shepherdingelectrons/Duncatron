from pyb import Pin
import random
import pyb
import select
import sys

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
        

        #if pinMode is not Pin.IN and label is not "CLK":
        if label is not "CLK":
            SignalList.append(self)

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
    if verbose:
        pinModeStr = "OUT" if CLK.pin.mode() else "IN"
        print("CLK: OFF ("+pinModeStr+")")
    signaln=0
    for s in SignalList:
        pinModeStr = "OUT" if s.pin.mode() else "IN"
        if report:
            if (s.value()==0 and s.active_low) or (s.value()==1 and s.active_low==False):
                print(s.label,": ON! ("+pinModeStr+")")
        else:
            if invert:
                s.on()
            else:
                s.off()
                if verbose: print(signaln,s.label,": OFF ("+pinModeStr+")")
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

def burnBIN(binfilename="test.bin",write=True,check=True):
    f = open(binfilename,"rb")
    data = f.read()
    f.close

    PC = 0
    size=len(data)
    if write:
        print("Writing...")
        for byte in data:
            writeMEM(PC,byte)
            PC+=1
            #print(hex(byte))
        print("Binary file",binfilename,"written, total bytes="+str(size))

    if check:
        PC=0
        read_errors = 0
        print("Reading...")
        for byte in data:
            readbyte = int(readMEM(PC)[0])
            if readbyte!=byte:
                print("Should be:",byte,"read:",readbyte,"at position:",PC)
                read_errors+=1
            PC+=1
        if read_errors ==0:
            print("Read back OK!")
        else:
            print("Read back errors:",read_errors)
    
    writePC(0)
    writeMAR(0)
    
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
            
def run(wait=0.0):
    CLK.off()
    off(verbose=False)
    opcode = 255
    # Skipping FETCH instruction for NOW
    #setI(machine_lang[0]) # set address

    #constants:
    I_REG = 1
    A_REG = 2
    U_REG = 3

    uart.read() # clear cacheua
    
    while True:
        
        for tick in range(0,8):
            Z = FLAG_Z.value()
            C = 1 # no carry
            INS = opcode

            uart_output = 0 # Debug flag for piping output to UART

            address = (Z<<12)|(C<<11)|(tick<<8)|INS
            control_byte0 = control0[address]
            control_byte1 = control1[address]
            control_byte2 = control2[address]

            MC_RESET = False
            #new_INS = False

            test_Uin = 0 #
            test_Uout = 0

            import select
            p = select.poll()
            p.register(sys.stdin)

            MP_STREAM_POLL_RD = const(1)
            _, flags = p.poll(0)[0]
            if flags & MP_STREAM_POLL_RD:
                cmd = sys.stdin.read(1)
                uart.write(cmd)

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

                if signal_name=="Ii" and bit==0:
                    uart_output = I_REG                             
                if signal_name=="MC_RESET" and bit==1:
                    MC_RESET = True
                if signal_name=="HALT" and bit==1:
                    return

                if signal_name=="INen" and bit==0: # Duncatron wants to send/receive UART maybe
                    test_Uin = 1
                
                if not override:
                    SignalList[s].value(bit)
                
                # end of signal for loop
            # tick for loop     
            I2 = 1 if INS&(1<<2) else 0
            I3 = 1 if INS&(1<<3) else 0
            a3_o0 = I3 ^ X.value() # XOR
            in0 = I2 ^ X.value() # XOR

            alu_addr = INS&(0b111) | (a3_o0)<<3
            #print("ALU_ADDR:",alu_addr)

            I6 = 1 if INS & (1<<6) else 0
            I7 = 1 if INS & (1<<7) else 0
            UARTmux = (I7<<2) | (I6<<1) | in0

            if test_Uin:
                if UARTmux==0: # Duncatron wants to send char but we control the Uin line
                    uart_output = U_REG
                if UARTmux==1: # Duncatron wants to receive char but we control the Uout line
                    Uin.on()
                
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
                            opcode = char
                            INS = opcode
                    elif uart_output==U_REG:
                        print(chr(char),end="")
                    else:
                        print("uart_output not supported!",uart_output)
                else:
                    print(n,"is not 1!",uart.read())
            
            uart_output=0
            if MC_RESET==True:
                break
            
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

def writePC(address):
    writeMAR(address,writePC=True)

def writeMAR(address,writePC=False):
    low = address & 0xFF
    high = (address>>8)&0xFF

    writeT(high)
    
    uart.writechar(low)
    microwait(1E3) # sending UART char

    T_IO.on() # Read from T onto HIGH
    T_EN.on()
    T_HL.on()
    
    Uin.on()
    if writePC:
        PCi.on()
    else:
        MARi.on()
    microwait(1E3)
    CLK.on()
    microwait(1E3)
    CLK.off()
    Uin.off()
    if writePC:
        PCi.off()
    else:
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
    
def testMEM(size=0x10000,write=False,seed=69):
    import random
    random.seed(seed)
    if write==True:
        print("Writing")
        for a in range(0,size):
            db = random.randint(0,256)
            writeMEM(a,db)
    print("Reading")
    random.seed(seed)
    mismatches = 0
    memory_map = 0x81
    
    for a in range(0,size):
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

def ProcessSignalLog():
    # uses global (sorry) dictonaries
    #    badSignals={}
    #    goodSignals={}
    
    for s in range(0,24):
        signalName = SignalList[s].label
        bad,badops = badSignals[signalName]
        good = goodSignals[signalName]

        print(signalName+": Good="+str(good)+" Bad="+str(bad)+ "Bad ops:",badops)
    

def Listen(numINS=10,startINS=0):
    maxCLKs = numINS*8
    print("Entering Listenng mode, waiting for CLK ticks")
    for i in [0,1,2]:
        listen_str = "LISTEN" if listen&(1<<i) else "SET"
        print("Bank"+str(i)+listen_str)

    print("CTRL+C to exit")
    prev_CLK = CLK.value()
    signal_log = []
    numCLK=0

    uart_output = 0
    #constants:
    I_REG = 1
    A_REG = 2
    U_REG = 3
    PC_low = 4
    MAR_low = 5

    instructions = instructon_str.split("#")
    tick = 0
    INS = startINS

    notfirst = False

    uart.read() #flush buffer
    while numCLK<maxCLKs:
        test_Uin = 0
        CLK_now = CLK.value()
        
        if CLK_now - prev_CLK == 1:
            # positive clock transition
            uart_output = 0 # No output by default
            #print("CLK up")
            numCLK+=1
            read_byte0 = 0
            read_byte1 = 0
            read_byte2 = 0

            Z = 1 # Not set
            C = 0 # Not set
            address = (Z<<12)|(C<<11)|(tick<<8)|INS
            control_byte0 = control0[address]
            control_byte1 = control1[address]
            control_byte2 = control2[address]
            
            for s in range(0,24):
                signal_value = SignalList[s].value()
                signal_name = SignalList[s].label
                signal_activelow = SignalList[s].active_low
                s_mask = s&7

                if signal_name not in badSignals:
                    badSignals[signal_name]=(0,[])
                if signal_name not in goodSignals:
                    goodSignals[signal_name]=0
                    
                # 0 1 2 3 4 5 6 7
                # 8 9 A B C D E F

                if s<8:
                    read_byte0 = read_byte0|(signal_value<<s_mask) # make new control byte
                    bit = 1 if control_byte0&(1<<s_mask) else 0 # get expected bit from control_byte file
                        
                elif s<16:
                    read_byte1 = read_byte1|(signal_value<<s_mask)
                    bit = 1 if control_byte1&(1<<s_mask) else 0
                else:
                    read_byte2 = read_byte2|(signal_value<<s_mask)
                    bit = 1 if control_byte2&(1<<s_mask) else 0

                if notfirst: # Don't include the first instruction
                    signal_str = str(INS)+"#"+instructions[INS]+"#"+str(tick)+"!"+str(bit)
                    
                    if signal_value!=bit:
                        freq,op = badSignals[signal_name]
                        freq+=1

                        if signal_str not in op:
                            op.append(signal_str)
                        badSignals[signal_name]=(freq,op)
                        print("Bad signal",signal_name,"in",signal_str)
                    else:
                        freq,op = badSignals[signal_name]
                        if signal_str in op:
                            print(signal_str,"also in badSignals for",signal_name)
                            
                        goodSignals[signal_name]+=1#(freq,op)
                    
                if signal_name=="Ii" and signal_value==0: # Active low Ii
                    uart_output = I_REG
                    
                if signal_name=="INen" and signal_value==0: # Duncatron wants to send/receive UART maybe
                    I2 = 1 if INS&(1<<2) else 0
                    I3 = 1 if INS&(1<<3) else 0
                    a3_o0 = I3 ^ X.value() # XOR
                    in0 = I2 ^ X.value() # XOR

                    I6 = 1 if INS & (1<<6) else 0
                    I7 = 1 if INS & (1<<7) else 0
                    UARTmux = (I7<<2) | (I6<<1) | in0
                    
                    if UARTmux==0: # Duncatron wants to send char but we control the Uin line
                        uart_output = U_REG
                        
                if signal_name=="PCi" and signal_value==1: #Active high PCi
                    uart_output = PC_low
                    
                if signal_name=="MARi" and signal_value==0: #Active low MARi
                    uart_output = MAR_low
          
            #print(cbyte0==control_byte0,cbyte1==control_byte1,cbyte2==control_byte2)
            #print(bin(cbyte0),bin(cbyte1),bin(cbyte2))
            #print(bin(control_byte0),bin(control_byte1),bin(control_byte2))

            #print(bin(control_byte0),bin(control_byte1),bin(control_byte2))
            #signal_log.append((control_byte0,control_byte1,control_byte2))
            tick+=1
            tick&=7
            if uart_output:
                Uout.on()
        #### End positive clock transition ####     
                    
        elif CLK_now - prev_CLK == -1: # Negative clock transition
            if uart_output!=0:#==I_REG:
                microwait(1E4)
                
                n = uart.any()
                if n==1:
                    char = uart.read()[0]
                    if uart_output==I_REG:
                            INS = char
                            notfirst = True
                            print("Instructon opcode=",INS,instructions[INS])
                            if tick!=2:
                                print("microtick count off!",tick)
                    elif uart_output==PC_low:
                        print("PC(low):",hex(char))
                    elif uart_output==MAR_low:
                        print("MAR(low):",hex(char))
                    elif uart_output==U_REG:
                        print("UART TX:",chr(char),hex(char),char)
                    else:
                        print("uart_output not supported!",uart_output)
                else:
                    print(n,"is not 1!",uart.read())
            
                uart_output=0 
                Uout.off()
            # Set control signals for signals without
            Z = 1 # Not set
            C = 0 # Not set
            address = (Z<<12)|(C<<11)|(tick<<8)|INS
            control_byte0 = control0[address]
            control_byte1 = control1[address]
            control_byte2 = control2[address]
            
            for s in range(0,24):
                signal_name = SignalList[s].label
                s_mask = s&7
                # 0 1 2 3 4 5 6 7
                # 8 9 A B C D E F

                override = False
                if s<8:                
                    bit = 1 if control_byte0&(1<<s_mask) else 0
                    override = listen_bank0 # don't set signals for banks we are listening to
                elif s<16:
                    bit = 1 if control_byte1&(1<<s_mask) else 0
                    override = listen_bank1
                else:
                    bit = 1 if control_byte2&(1<<s_mask) else 0
                    override = listen_bank2

                if not override:
                    SignalList[s].value(bit)
        #### End negative clock transition ####  
        
        prev_CLK = CLK_now
    #### End while loop
    ProcessSignalLog()

def showsigs(opcode,tick,C=1,Z=0):
    address = (Z<<12)|(C<<11)|(tick<<8)|opcode
    control_byte0 = control0[address]
    control_byte1 = control1[address]
    control_byte2 = control2[address]

    active_list = []
    actual_actives = []

    match = True
    measured_byte0 = 0
    measured_byte1 = 0
    measured_byte2 = 0
    

    for s in range(0,24):
        active_low = SignalList[s].active_low
        s_mask=s&7
        display_LED = 0
        active_sig = 0
        
        if s<8:
            raw_bit = 1 if control_byte0 &(1<<s_mask) else 0
            display_bit = raw_bit
            if s==5 or s==6: # invert MARi and Ro
                display_bit = 1 - display_bit
            if s==7: #MC_RESET:
                display_bit = 0 # tied to ground
        elif s<16:
            raw_bit = 1 if control_byte1 &(1<<s_mask) else 0
            display_bit = raw_bit
            if s==8 or s==9: #T_HL and T_IO
                display_bit = 1 - display_bit
        else:
            raw_bit = 1 if control_byte2 &(1<<s_mask) else 0
            display_bit = raw_bit
            
            if s==20: #X
                display_bit = 1 - display_bit

        actual_value = SignalList[s].value()
        if s<8:
            measured_byte0 |= (actual_value<<s_mask)
        elif s<16:
            measured_byte1 |= (actual_value<<s_mask)
        else:
            measured_byte2 |= (actual_value<<s_mask)
        
        if actual_value!=raw_bit:
            match=False

        if (not active_low and display_bit) or (active_low and not display_bit):
            display_LED = 1
        else:
            display_LED = 0
            
        if s==10 or s==20: print(":",end='')
        print(str(display_LED),end='')

        if (not active_low and raw_bit) or (active_low and not raw_bit):
            active_list.append(SignalList[s].label)

        if (not active_low and actual_value) or (active_low and not actual_value):
            actual_actives.append(SignalList[s].label)

    return (match, active_list, actual_actives,measured_byte0,measured_byte1,measured_byte2)
   
def sigs(ins,tick):
    for i in range(0,8):
        match, active_list, actual_actives,mb0,mb1,mb2 = showsigs(ins,i)
        if tick==i:            
            if match:
                print("-Matched!")
            elif not (len(active_list)==1 and "MC_RESET" in active_list and len(actual_actives)==0):
                print("-Mis-matched :<")
                for sig in active_list:
                    if sig not in actual_actives: #Signal should be on but isn't
                        print(sig,"not active :(")
                    else:
                        print(sig,"is active")   #Signal should be on and is
                for sig in actual_actives:
                    if sig not in active_list:   #Signal is on but shouldn't be!
                        print(sig,"Shouldn't be on! :(")
                print(ins,tick,mb0,mb1,mb2)
                searchsigs(ins,tick,mb0,mb1,mb2)
            else:
                print("(only MC_RESET)")
        else:
            print()

def searchsigs(original_op,original_tick,mb0,mb1,mb2):
    instructions = instructon_str.split("#")
    min_diff = 255
    for address in range(0,1<<12):
        #address = (Z<<12)|(C<<11)|(tick<<8)|opcode
        opcode=address&0xff
        tick=(address>>8)&7
        C=(address>>11)&1
        Z=(address>>12)&1
        
        if mb0==control0[address]:
            op_diff = bin(original_op^opcode).count("1")
            tick_diff = bin(original_tick^tick).count("1")
            diff=op_diff+tick_diff
            #if diff<min_diff:
            if diff<2:
                starred="\n"
                if op_diff==1 and tick_diff==0:
                    bits = bin(original_op^opcode)
                    bit_pos = len(bits)-bits.find("1")-1
                    starred=":*"+str(bit_pos)+"\n"
                print(diff,instructions[opcode],"|",original_op,opcode,op_diff,"|",original_tick,tick,tick_diff,"|",C,"|",Z,end=starred)
            min_diff = diff
micros = pyb.Timer(2, prescaler=83, period=0x3fffffff)

listen = True

listen_bank0 = listen
listen_bank1 = listen
listen_bank2 = listen
   
listen = listen_bank2<<2 | listen_bank1<<1 | listen_bank0

PinMode_CLK = Pin.IN if listen else Pin.OUT_PP
PinMode0 = Pin.IN if listen_bank0 else Pin.OUT_PP
PinMode1 = Pin.IN if listen_bank1 else Pin.OUT_PP
PinMode2 = Pin.IN if listen_bank2 else Pin.OUT_PP

CLK = Signal("CLK","Y3", PinMode_CLK, active_low = False)

Ai = Signal("Ai","Y4", PinMode0, active_low=True)
ALUo = Signal("ALUo","Y5", PinMode0, active_low=True)
Ii = Signal("Ii","Y6", PinMode0, active_low=True)
PCo = Signal("PCo","Y7", PinMode0, active_low=True)
PCinc = Signal("PCinc","Y8", PinMode0, active_low=False)
MARi = Signal("MARi","X9", PinMode0, active_low=True)
Ro = Signal("Ro","X10", PinMode0, active_low=True)
MC_RESET = Signal("MC_RESET","X11", PinMode0, active_low=False)

T_HL = Signal("T_HL","X12", PinMode1, active_low=False)
T_IO = Signal("T_IO","X17", PinMode1, active_low=False)
T_EN = Signal("T_EN","X18", PinMode1, active_low=False)
Ri = Signal("Ri","X19", PinMode1, active_low=False)
Fi = Signal("Fi","X20", PinMode1, active_low=True)
SPdec = Signal("SPdec","X21", PinMode1, active_low=False)
SPinc = Signal("SPinc","X22", PinMode1, active_low=False)
Bi = Signal("Bi","X1", PinMode1, active_low=True)

PCi = Signal("PCi","X2", PinMode2, active_low=False)
Ao = Signal("Ao","X3", PinMode2, active_low=True)
OUTen = Signal("OUTen","X4", PinMode2, active_low=True)
INen = Signal("INen","X5", PinMode2, active_low=True)
X = Signal("X","X6", PinMode2, active_low=False)
Fo = Signal("Fo","X7", PinMode2, active_low=True)
HALT = Signal("HALT","X8", PinMode2, active_low=False) # Use as input for FLAG_Z
SPo = Signal("SPo","Y9", PinMode2, active_low=True)

if not listen_bank2:
    FLAG_Z = Pin("X8", Pin.IN, Pin.PULL_DOWN)
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
writePC(0)
writeMAR(0)
#test_signals(waittime=0.05)
#off(invert=True)
#microwait(1E6)
#off()
#mock_working()
print("Ready")
#test_signals(waittime=0.2, verbose=False,tick=True)

control0 = OpenControlFile("control_EEPROM0.txt")
control1 = OpenControlFile("control_EEPROM1.txt")
control2 = OpenControlFile("control_EEPROM2.txt")

##print("hello")
##from assembler import asm
##print(asm("MOV A,B"))

##print("imported assembler")
##execute("INC A")
##while True:
##    CLK.on()
##    microwait(1E5)
##    CLK.off()
##    microwait(1E5)

instructon_str="INC A#SUB A,0x@@#CMP A,0x@@#DEC A#ADDC A,0x@@#SUBC A,0x@@#CMPC A,0x@@#MOV A,U#INC B#MOV U,A#POP PC#DEC B#MOV B,U#MOV AB,0x@@@@#MOV A,B#MOV B,A#ADD A,r0#SUB A,r0#CMP A,r0#MOV U,0x@@#ADDC A,r0#SUBC A,r0#CMPC A,r0#MOV [r0r1],0x@@#MOV AB,r0r1#MOV AB,r2r3#MOV AB,r4r5#MOV A,r1#MOV B,r1#MOV A,0x@@#MOV A,[0x@@]#MOV A,[0x@@@@]#ADD A,r2#SUB A,r2#CMP A,r2#MOV [r2r3],0x@@#ADDC A,r2#SUBC A,r2#CMPC A,r2#MOV [r2r3],A#MOV A,r3#MOV B,r3#POP A#MOV B,0x@@#MOV B,[0x@@]#MOV B,[0x@@@@]#POP B#PUSH A#ADD A,r4#SUB A,r4#CMP A,r4#MOV [r4r5],0x@@#ADDC A,r4#SUBC A,r4#CMPC A,r4#MOV [r4r5],A#MOV A,r5#MOV B,r5#MOV [0x@@],A#MOV [0x@@@@],A#PUSH 0x@@#POP T#PUSH r5#MOV [0x@@],r5#ADD A,0x@@#SUB A,B#CMP A,B#MOV r0r1,AB#ADDC A,B#SUBC A,B#CMPC A,B#MOV r1,A#MOV r0r1,0x@@@@#MOV r0,A#MOV r0,B#MOV r0,0x@@#MOV r1,B#MOV r1,0x@@#MOV r1,[0x@@]#MOV r1,[0x@@@@]#INC r0#SUB A,r1#CMP A,r1#DEC r0#ADDC A,r1#SUBC A,r1#CMPC A,r1#MOV [r0r1],A#INC r1#MOV r0,r1#MOV r1,r0#DEC r1#INC r0r1#POP r1#PUSH r1#MOV [0x@@],r1#ADD A,r3#SUB A,r3#CMP A,r3#MOV r0r1,r2r3#ADDC A,r3#SUBC A,r3#CMPC A,r3#MOV A,[r2r3]#MOV r0,r3#MOV r1,r2#MOV r0,[0x@@]#MOV r0,[0x@@@@]#MOV r0,r2#MOV r1,r3#PUSH r3#MOV [0x@@],r3#ADD A,r5#SUB A,r5#CMP A,r5#MOV r0r1,r4r5#ADDC A,r5#SUBC A,r5#CMPC A,r5#MOV A,[r4r5]#MOV r0,r5#MOV r1,r4#POP r0#MOV [0x@@@@],r5#MOV r0,r4#MOV r1,r5#NOR A,B#RCL A#ADD A,B#MOV r2r3,AB#MOV r2r3,0x@@@@#MOV r2,A#MOV r3,A#RETI#MOV r3,0x@@#MOV r3,[0x@@]#MOV r2,B#MOV r2,0x@@#MOV r2,[0x@@]#MOV r2,[0x@@@@]#MOV r3,B#MOV r3,[0x@@@@]#POP r3#PUSH B#ADD A,r1#MOV A,[r0r1]#MOV r2r3,r0r1#MOV A,r0#MOV B,r0#MOV r3,r0#PUSH r0#MOV [0x@@],r0#MOV r2,r1#POP r2#MOV [0x@@@@],r1#OR A,B#MOV r2,r0#MOV r3,r1#NOR A,0x@@#MOV A,F#INC r2#MOV A,r2#MOV B,r2#DEC r2#MOV r3,r2#PUSH r2#MOV [0x@@],r2#MOV [0x@@@@],r2#INC r3#MOV r2,r3#MOV [0x@@@@],r3#DEC r3#INC r2r3#AND A,B#PUSH F#POP F#MOV r2r3,r4r5#MOV A,r4#MOV B,r4#MOV r2,r4#MOV r3,r4#PUSH r4#MOV [0x@@],r4#MOV [0x@@@@],r4#MOV r2,r5#XOR A,B#NAND A,B#OR A,0x@@#MOV r3,r5#AND A,0x@@#PUSH_PC+1#INT#MOV r4r5,AB#MOV r4r5,0x@@@@#MOV r4,A#MOV r4,0x@@#MOV r5,A#MOV r5,0x@@#MOV r5,[0x@@]#MOV r5,[0x@@@@]#MOV r4,B#MOV r4,[0x@@]#MOV r4,[0x@@@@]#POP r4#MOV r5,B#POP r5#MOV [0x@@],B#MOV [0x@@@@],B#MOV r4r5,r0r1#MOV r4,r0#MOV [0x@@@@],r0#JZ 0x@@@@#MOV r5,r0#JNZ 0x@@@@#JE 0x@@@@#NOT A#MOV r4,r1#XOR A,0x@@#NAND A,0x@@#JNE 0x@@@@#MOV r5,r1#JG 0x@@@@#JGE 0x@@@@#JL 0x@@@@#MOV r4r5,r2r3#MOV r4,r2#JLE 0x@@@@#JMP 0x@@@@#MOV r5,r2#JC 0x@@@@#JNC 0x@@@@#SHR A#MOV r4,r3#CALL_Z 0x@@@@#CALL_NZ 0x@@@@#CALL_E 0x@@@@#MOV r5,r3#CALL_NE 0x@@@@#CALL_G 0x@@@@#CALL_GE 0x@@@@#SHL A#CALL_L 0x@@@@#CALL_LE 0x@@@@#DEC r4#INC r4#MOV r5,r4#CALL 0x@@@@#CALL_C 0x@@@@#INC r5#MOV r4,r5#CALL_NC 0x@@@@#DEC r5#INC r4r5#RET#HALT#NOP"
badSignals={}
goodSignals={}

if listen:
    print("In LISTENING mode")
else:
    print("In CONTROL mode")

