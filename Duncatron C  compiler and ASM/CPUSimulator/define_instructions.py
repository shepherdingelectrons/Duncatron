def add_instruction(ins,pos,addresses=None,microcode_lines=None,quiet=False):
    if pos==None: # Find free position first:
        if addresses==None:
            print("ERROR! Valid address list required!!")
        for i in addresses:
            pos = i
            if instruction_set[pos]=="":
                break
    if instruction_set[pos]!="":
        if not quiet: print("ERROR: Instruction position",pos,"is already occupied with:",instruction_set[pos],". Cannot add:",ins)
        return -1
    instruction_set[pos]=ins

    if microcode_lines!=None:
        define_microcode(pos,microcode_lines)

    return pos # For those that want it!

def customasm(ins,op):
    #https://hlorenzi.github.io/customasm/web/
    # Instructions only have one 16-bit or 8-bit number
    prepost=""
    post=""
    u16=ins.count("0x@@@@")
    ins=ins.replace("0x@@@@","{addr16: u16}")
    if u16>0: post=" @addr16"
    
    a8=ins.count("[0x@@]")
    ins=ins.replace("[0x@@]","[{addr8: u8}]")
    if a8>0: post=" @addr8"

    loc = ins.find("0x@@00")
    ins=ins.replace("0x@@00","{addr16: u16}")
    if loc>0:
        prepost = "{assert((addr16[7:0]==0)),"
        post = " @addr16[15:8]}"
        #CALL Z,{addr16: u16} => {assert((addr16[7:0]==0)),0xe5e7 @addr16[15:8]}

    u8=ins.count("0x@@")
    ins=ins.replace("0x@@","{value8: u8}")
    if u8>0:
        post=" @value8"

    tilde = ins.count("~") #discard from opcode and add padding byte
    if tilde>0:
        ins=ins.replace("~","")
        post="00"
   
    ruledef = ins+" => "+prepost+"0x{:02x}".format(op) + post
    return ruledef.lower()

def get_instruction_properties(tilde,op):

    flags = "-"
    PC = tilde 
    regs = ""
    ALU_ins = ""
    cycles = 0
    zp = "  "
    
    for m in microcode[op]:
        if m!="" and "MC_reset" not in m:
            cycles+=1
        if "Fi" in m:
            if "T_EN" in m:
                print("T_EN at same time as Fi!")
            flags = "Z,C,N"
            ALU_a3 = 1 if op&(1<<3) else 0
            if "X" in m:
                ALU_a3 = 1 - ALU_a3
            ALU_op = (ALU_a3<<3) | (op&0b111)
            
            t = ALU_INSTRUCTIONS[ALU_op]
            if " " in t:
                t = t[:t.index(" ")]
            
            ALU_ins += t +","
            
        if "PCinc" in m:
            PC +=1
        if "Ai" in m:
            if "A" not in regs:
                regs +="A,"
        if "Bi" in m:
            if "B" not in regs:
                regs +="B,"
            #reg_names = ["A","B","r0","r1","r2","r3","r4","r5"]
        if "T_EN" in m and "T_IO" not in m:# or "T_IO?" in m: # Need to be careful whether this signal means input or output when asserted. T_IO = 1 means OUTPUT, reading to register
            if "T" not in regs:
                regs +="T,"
        if "MARi" in m:
            if "PCo" not in m and "T_IO" not in m and "SPo" not in m:
                zp = "ZP"
                
            
        if "INen" in m: # Need to take X-signal into account when looking at written registers
            # 0b i2 i1 o2 o1 x1/o0 a2/i0 a1 a0
            in_reg2 = 1 if op&(1<<7) else 0
            in_reg1 = 1 if op&(1<<6) else 0
            in_reg0 = 1 if op&(1<<2) else 0

            
            if "X" in m: in_reg0 = 1-in_reg0 

            REG_in = (in_reg2<<2)|(in_reg1<<1)|in_reg0
            if REG_in!=1: # _Uout is a special case, and is not an input register!
                reg_name = reg_names_IN[REG_in]
                if not reg_name in regs:
                    regs += reg_name+","
    if regs!="":
        regs=regs[:-1] # remove comma
    else:
        regs=" "
        
    temp_prop = {}
    temp_prop["flags"]=flags
    temp_prop["PC"]=PC
    temp_prop["regs"]=regs
    temp_prop["ALU_ins"]=ALU_ins
    temp_prop["cycles"]=str(cycles)
    temp_prop["zp"]=zp
    
    return temp_prop
    
def info_table(ins, op):
    post=""
    u16=ins.count("0x@@@@")
    ins=ins.replace("0x@@@@","0xHIJK")
    if u16>0: post="HIJK"
    
    a8=ins.count("[0x@@]")
    ins=ins.replace("[0x@@]","[0xHI]")
    if a8>0: post="HI"

    u8=ins.count("0x@@")
    ins=ins.replace("0x@@","0xHI")
    if u8>0: post="HI"

    tilde=0
    loc=ins.count("~")
    ins=ins.replace("~","")
    if loc>0:
        tilde=1
        post="00"
    
    code=ins.split(" ")[0]    
##    flags = "-"
##    PC = tilde # 
##    regs = ""
##    ALU_ins = ""
##    cycles = 0

    # What might change under different ZC conditions for the same opcode?
    # cycle count (cycles)
    # registers changed (regs)
    props=[{}]*4

    props[0]=get_instruction_properties(tilde,op)
    props[1]=get_instruction_properties(tilde,op+256)
    props[2]=get_instruction_properties(tilde,op+512)
    props[3]=get_instruction_properties(tilde,op+768)

    flags = props[0]["flags"]
    PC = props[0]["PC"]
    regs = props[0]["regs"]
    ALU_ins = props[0]["ALU_ins"]
    cycles = props[0]["cycles"]
    zp = props[0]["zp"]

    diff=1
    if props[0]["cycles"]==props[1]["cycles"]==props[2]["cycles"]==props[3]["cycles"]:
        diff=0
    if diff: cycles+="|"+props[1]["cycles"]+"|"+props[2]["cycles"]+"|"+props[3]["cycles"]

    diff=1
    if props[0]["regs"]==props[1]["regs"]==props[2]["regs"]==props[3]["regs"]:
        diff=0
    if diff: regs+="|"+props[1]["regs"]+"|"+props[2]["regs"]+"|"+props[3]["regs"]
               
    opcode = "0x{:02x}".format(op)
    machine_code = opcode+post
    PC = "PC=PC+"+str(PC)
    
    if ALU_ins!="":
        ALU_ins=ALU_ins[:-1]
    else:
        ALU_ins=" "
        
    if len(machine_code)<8: machine_code=machine_code+"\t"
    if len(ins)<8: ins=ins+"\t"
# opcode, instruction, usage, machine code, flags changed, registers changed, total cycles, PC change,
# add SP change?

    info = opcode+"\t"+code+"\t"+ins+"\t"+machine_code+"\t"+flags+"\t"+regs+"\t"+cycles+"\t"+PC+"\t"+ALU_ins+"\t"+zp
    return info

def define_signal(signal,active_low=False,position=None):
    if signal in signals:
        print("ERROR! Signal,'",signal,"' already defined!")
        return
    if position==None:
        position = len(signals)
    signals[signal]=(position,active_low)

def define_microcode(opcode,lines,ZC=None):
    # ZC = 0b00, 0b01, 0b10, 0b11
    if ZC!=None:
        ZC = ZC<<8 # 0,256,512,768
        
    if type(opcode)==type(""):
        opcode = asm(opcode)[0] # get opcode straight from assembler, helps if instructions are reordered

    for i,l in enumerate(lines):
        for s in l: # inspect each signal in each microcode line
            if s not in signals:
                print("ERROR! Signal '",s,"' not found in signal definitions for opcode:",opcode)
                pass
        if ZC==None:
            microcode[opcode][i]=l
            microcode[opcode+256][i]=l
            microcode[opcode+512][i]=l
            microcode[opcode+768][i]=l
        else:
            microcode[opcode+ZC][i]=l # This lets us do conditional JMPing later           
            
    if i<7:        
        if ZC==None:
            if not "MC_reset" in microcode[opcode][i]:
                microcode[opcode][i+1] = ["MC_reset"] # microcounter reset, add here automatically if not added manually
                microcode[opcode+256][i+1] = ["MC_reset"]
                microcode[opcode+512][i+1] = ["MC_reset"]
                microcode[opcode+768][i+1] = ["MC_reset"]
        else:
            if not "MC_reset" in microcode[opcode+ZC][i]:
                microcode[opcode+ZC][i+1] = ["MC_reset"]
            

def get_microcode_int(controls):
    total = 0
    for signal_name in signals:
        signal_id = signals[signal_name][0]
        active_low = signals[signal_name][1]

        signal = 1 if active_low else 0 # Off by default (off is different depending on whether signal is active low or not)
        if signal_name in controls:
            signal = 0 if active_low else 1 # Turn on ('on' is context dependent)

        total |= (signal<<signal_id)
    return total

# Instruction format:
# 0b i2 i1 o2 o1 x1 a2 a1 a0

# a3 = XOR(X-sig,x1)
# o0 = XOR(X-sig,x1) = a3
# i0 = XOR(X-sig,a2)

def add_carry_set_clear():
    # do ANY logic instruction to clear carry - apart from SHL A...!
    #ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B","SUBC A,B","CMPC A,B","NOT A","SHL A","XOR A,B","NAND A,B","OR A,B","INC A","AND A,B", "NOR A,B", "CLR A"]
    CLRC = ["NOT A","XOR A,B","NAND A,B","OR A,B","AND A,B", "NOR A,B"]#, "CLR A"]
    valid=[]
    for alu_pos,c in enumerate(ALU_INSTRUCTIONS):
        if c in CLRC:
            for x in range(0,256):
                if 0b1111&x==alu_pos and x not in valid:
                    valid.append(x)
    add_instruction("CLRC",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["Fi"]])

    # Set carry by doing a CMP to 0 (SUB 0)
    # Sub = 0b0001
    # B is set to 0 by asserting X (active low, X=0) and using pull-up/down resistors on databus with no register output
   # add_instruction("SETC",pos=None,addresses=[a for a in range(0,256) if a&0b1111==0b0001],microcode_lines=[FETCH0,FETCH1,["Bi","X"],["Fi"]])
    
def add_ALU_LOGIC():
    # A = ALU(A, B): # Logic functions with A and B
    # 0b - x x x x a3 1 a1 a0
    # 4 : 0b0100: NOT A
    # 5 : 0b0101: A NOR B
    # 6 : 0b0110: A NAND B
    # 7 : 0b0111: NOT B
    # 12: 0b1100: A XOR B
    # 13: 0b1101: A AND B
    # 14: 0b1110: SHL A
    # 15: 0b1111: RCL A


    # NEW:

    # 0 : 0b0000: ADD A,reg
    # 1 : 0b0001: SUB A,reg
    # 2 : 0b0010: CMP A,reg
    # 3 : 0b0011: DEC A
    
    # 4 : 0b0100: ADDC A,reg
    # 5 : 0b0101: SUBC A,reg
    # 6 : 0b0110: CMPC A,reg
    # 7 : 0b0111: NOT A

    # 8 : 0b1000: NOT B
    # 9 : 0b1001: A NOR B
    # 10: 0b1010: A NAND B
    # 11: 0b1111: A XOR B
    
    # 12: 0b1100: INCC rn:rn+1 (uses ADDC ALU settings)
    # 13: 0b1101: A AND B
    # 14: 0b1110: SHL A
    # 15: 0b1111: RCL A

    
    #ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B","SUBC A,B","CMPC A,B","NOT A","NOT B","A NOR B","A NAND B","A XOR B","INC A","A AND B", "SHL A", "RCL A"]

    #ALU_LOGIC = [("NOT A",7),("NOT B",8),("NOR A,B",9),("NAND A,B",10),("XOR A,B",11),("AND A,B",13),("SHL A",14),("RCL A",15),\
    #             ("NOR A,0x@@",7),("NAND A,0x@@",10),("XOR A,0x@@",11),("AND A,0x@@",13)]
    ALU_LOGIC = []

    for ai,a in enumerate(ALU_INSTRUCTIONS):
        m = a[:3]
        if m!="ADD" and m!="SUB" and m!="CMP" and m!="DEC" and m!="INC":
            ALU_LOGIC.append((a,ai)) # i.e. AND A,B
            if ",B" in a:
                b=a.replace(",B",",0x@@")  # i.e. AND A,0x@@
                ALU_LOGIC.append((b,ai))
    
    for alu_ins in ALU_LOGIC:

        ins,lower4bits = alu_ins
        
        u8=ins.count("0x@@") # Uses 8-bit immediate
        changeA = ["ALUo","Ai","Fi"] # By default (unless a CMP instruction), put ALU output into A and change Flags
            
        valid = [a for a in range(0,256) if (a & 0b1111)==lower4bits]
        
        if u8>0: #microcode here for putting value into B register
            add_instruction(ins,pos=None,addresses=valid, microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","Bi","PCinc"],changeA])
        else:
            pos=add_instruction(ins,pos=None,addresses=valid, microcode_lines=[FETCH0,FETCH1,changeA],quiet=True)  # Uses B register directly
            if pos==-1:
                a3 = 1 if lower4bits&(1<<3) else 0
                a210 = lower4bits&0b111
                a3 = 1-a3 # Invert a3 and assert X-signal
                valid = [a for a in range(0,256) if (a & 0b1111)==(a3|a210)]
                changeA.append("X")
                add_instruction(ins,pos=None,addresses=valid, microcode_lines=[FETCH0,FETCH1,changeA])
                
def add_ALU_ARITHMETIC():
    # A = ALU(A, out_reg):
    # 0b -  "o0" o2 o1 a3 0 a1 a0    # o0 can be set to 1 if necessary by X-signal for output to bus
    # "o0" bit is set so that the instruction can be addressed correctly, but is still of course wired to the x1 position.

    # 0 : 0b0000: ADD A,reg
    # 1 : 0b0001: SUB A,reg
    # 2 : 0b0010: CMP A,reg
    # 3 : 0b0011: DEC A
    
    # 4 : 0b0100: ADDC A,reg
    # 5 : 0b0101: SUBC A,reg
    # 6 : 0b0110: CMPC A,reg
    # 7 : 0b0111: NOT A

    # 8 : 0b1000: NOT B, now OR A,B
    # 9 : 0b1001: A NOR B
    # 10: 0b1010: A NAND B
    # 11: 0b1111: A XOR B
    
    # 12: 0b1100: INCC rn:rn+1 (uses ADDC ALU settings)
    # 13: 0b1101: A AND B
    # 14: 0b1110: SHL A
    # 15: 0b1111: RCL A
    

    #reg_names_OUT = ["A","B","r0","r1","r2","r3","r4","r5"] 

    #ALU_ARITHMETIC = [("ADD A,B",0),("SUB A,B",1),("CMP A,B",2),("ADDC A,B",4),("SUBC A,B",5), ("CMPC A,B",6)]
    ALU_ARITHMETIC = []
    for ai,a in enumerate(ALU_INSTRUCTIONS):
        m = a[:3]
        if m=="ADD" or m=="SUB" or m=="CMP":
            ALU_ARITHMETIC.append((a,ai))

    #reg_names = ["A","B","r0","r1","r2","r3","r4","r5"]

    # INC = (x + 255) + C = x + 256 = x+1
    
    for op,ins in enumerate(ALU_ARITHMETIC):
        op = ins[1]
        ins = ins[0]
        for reg_index, reg in enumerate(reg_names):
            changeA = ["ALUo","Ai","Fi"] # By default (unless a CMP instruction), put ALU output into A and change Flags:
            if ins[:3]=="CMP": changeA = ["Fi"] # Just change the flags, not A register

            o0 = 1 if (reg_index&1) else 0
            o1 = 1 if (reg_index&2) else 0
            o2 = 1 if (reg_index&4) else 0
            a3 = 1 if (op&8) else 0

            #0b x x o2 o1 0 a2 a1 a0
            addr =  (o2<<5) | (o1<<4) | (a3<<3) | (op&0b111) # this address and only this address.      

            valid = [addr,addr|(1<<6),addr|(1<<7),addr|(1<<7)|(1<<6)]
            
            if reg!="A":
                new_ins = ins.replace(",B",","+reg)
                if reg!="B":
                    setB = ["OUTen","Bi"]
                    if o0!=a3: # then X signal needs to be set to toggle a3 to correct value for output address
                        setB = ["OUTen","X","Bi"]
                    add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,setB,changeA])
                else:
                    add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,changeA]) # B is already in B!
            else:
                new_ins = ins.replace(",B",",0x@@")
                add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","Bi","PCinc"],changeA])  # Uses B register directly

def add_ALU_inc_dec():
    # INC register:               (i0)      # ALU controls for INC A = 0b0000 (=ADD)
    #           0b i2 i1 o2 o1 o0  0 0  0   # X-signal asserted for ALU as necessary to set a3==0 for B,r1,r3 and r5
    # inc A     0b 0  0  0  0  0   0 0  0   # Output reg address is fully defined in instruction 
    # inc B     0b 0  0  0  0  1   0 0  0   # Input reg address, need to assert X-signal where o0!=0, i.e. B, r1, r3 and r5
    # inc r0    0b 0  1  0  1  0   0 0  0
    # inc r1    0b 0  1  0  1  1   0 0  0   # means for B, r1, r3 and r5 we can output from ALU straight into input register with X-signal asserted
    # inc r2    0b 1  0  1  0  0   0 0  0   # also means for A, r0, r2 and r4 we can output from ALU into input register (with no X-signal asserted)
    # inc r3    0b 1  0  1  0  1   0 0  0
    # inc r4    0b 1  0  1  1  0   0 0  0
    # inc r5    0b 1  0  1  1  1   0 0  0

    #ALU_ARITHMETIC = [("ADD A,B",0),("SUB A,B",1),("CMP A,B",2),("ADDC A,B",8),("SUBC A,B",9), ("CMPC A,B",10)]
    
    #reg_names = ["A","B","r0","r1","r2","r3","r4","r5"]
    
    for reg_index, reg in enumerate(reg_names):
        o0 = 1 if (reg_index&1) else 0
        o1 = 1 if (reg_index&2) else 0
        o2 = 1 if (reg_index&4) else 0

        i1 = o1
        i2 = o2

        addr = (i2<<7) | (i1<<6) | (o2<<5) | (o1<<4) | (o0<<3) | (0<<2) | (0<<1) | (0<<0) # this address and only this address
        new_ins = "INC "+reg # Uses ADD control signals (0b0000)
        
        valid = [addr]
        if reg=="A":
            changeREG = ["ALUo","Ai","Fi"]
            valid=[a for a in range(0,256) if (a&0b111)==0b000] # Only need to make sure a2=0,a1=a0=0
            # B is set to 1, relies on lower 8-bit bus having suitable pull-up/down resistors! LSB could be weakly pulled down with "X" so that 0 or 1 can be set?
            # d0 -----[1k]----X
            #      |
            #      q0 on output register (can be tri-stated)
            #
            pos=add_instruction(new_ins,pos=None,addresses=valid)
            if pos&0b1000 == 0b1000:
                changeREG.append("X") # need to use X signal to toggle a3
            define_microcode(pos,[FETCH0,FETCH1,["Bi","X"],changeREG]) # This uses X to pullup lower databus to 0x01
            
        elif reg=="B":
            valid=[a for a in range(0,256) if (a&0b111)==0b000] # Only need to make sure a2=0,a1=a0=0
            # A is set to 1, using pull-up/down resistors on data bus
            # Need to assert X signal so that a3=0
            pos=add_instruction(new_ins,pos=None,addresses=valid)#,microcode_lines=[FETCH0,FETCH1,["Ai"],["X","ALUo","Bi","Fi"]])
            if pos&0b1000 == 0b1000:
                define_microcode(pos,[FETCH0,FETCH1,["Ai","X"],["X","ALUo","Bi","Fi"]]) # This uses X to pullup lower databus to 0x01
            else:
                define_microcode(pos,[FETCH0,FETCH1,["Ai","X"],["ALUo","Bi","Fi"]]) # This uses X to pullup lower databus to 0x01
        else:
            setA = ["OUTen","Ai"]
            changeREG = ["ALUo","INen","Fi"]
            out = reg_index # 0-7
            if o0==1: # then X signal needs to be set to toggle a3 to 0 (and set correct input address)
                changeREG = ["X","ALUo","INen","Fi"]

            if reg=="r4":
                # print("Hijacking",reg)
                # hijack the "INC r4" code to not block position for NOT B
                # INC register:               (i0)      # ALU controls for INC A = 0b0000 (=ADD)
                #           0b i2 i1 o2 o1 o0  0 0  0
                # INC  0b1100
                # ADDC 0b0100
                # ADD  0b0000
                
                # Try ADDC (0b0100) position for r4, then assert X signal to invert i0 to zero and set ALU=0b1100 as required
                
                addr = (i2<<7) | (i1<<6) | (o2<<5) | (o1<<4) | (0<<3) | (1<<2) | (0<<1) | (0<<0)
                changeREG.append("X")
                valid = [addr]
                add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["Bi","X"],setA,changeREG])
##            elif reg=="r5":
##                print("Hijacking",reg)
##
##                addr = (i2<<7) | (i1<<6) | (o2<<5) | (o1<<4) | (1<<3) | (1<<2) | (0<<1) | (0<<0)
##                valid = [addr]
##                add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["Bi"],setA,changeREG])
##                # Try 0b1000 (OR), then
            else:
                add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["Bi","X"],setA,changeREG])
       
    # DEC register:
    # 0b i2 i1 o2 o1 o0  1  1  1     # dec r0
    #                            (i0)
    #           0b i2 i1 o2 o1 o0 0  1  1   # ALU controls for DEC A = 0b0011
    # dec A     0b 0  0  0  0  0  0  1  1   # X-signal asserted for ALU to set a3=0 for B,r1,r3,r5
    # dec B     0b 0  0  0  0  1  0  1  1   # Output reg address is fulled defined in instructions
    # dec r0    0b 0  1  0  1  0  0  1  1   # Input reg address need to assert X-signal where o0=1, i.e. B, r1, r3 and r5
    # dec r1    0b 0  1  0  1  1  0  1  1   # means for  A, r0, r2 and r4 we can output from ALU straight into input register
    # dec r2    0b 1  0  1  0  0  0  1  1   # means for B, r1, r3 and r5 we can output from ALU into input register with X-signal asserted
    # dec r3    0b 1  0  1  0  1  0  1  1
    # dec r4    0b 1  1  1  1  0  0  1  1
    # dec r5    0b 1  1  1  1  1  0  1  1

        addr = (i2<<7) | (i1<<6) | (o2<<5) | (o1<<4) | (o0<<3) | (0<<2) | (1<<1) | (1<<0) # this address and only this address
        new_ins = "DEC "+reg

        valid = [addr]
        if reg=="A":
            changeREG = ["ALUo","Ai","Fi"]
##            if o0==0: # then X signal needs to be set to toggle a3 to 1, and i0=0 (=x0)
##                changeREG = ["X","ALUo","Ai","Fi"]
            valid=[a for a in range(0,256) if (a&0b111)==0b011] # Only need to make sure a2=0, a1=a0=1
            pos=add_instruction(new_ins,pos=addr)
            if pos&0b1000==0b1000:
                changeREG.append("X")
            define_microcode(pos,[FETCH0,FETCH1,changeREG])
            
        elif reg=="B":
            setA = ["OUTen","Ai"] # output address always fully defined
            changeREG = ["ALUo","Bi","Fi","X"]
            valid=[a for a in range(0,256) if (a&0b111111)==0b001011] # B out address is (001), DEC is 0b011
            add_instruction(new_ins,pos=addr,microcode_lines=[FETCH0,FETCH1,setA,changeREG])
            
        else:
            setA = ["OUTen","Ai"] # output address always fully defined
            changeREG = ["ALUo","INen","Fi"]
            if o0==1: # need to assert X so a3 toggled to '0' and i0 toggled to '1' (=o0)
                changeREG = ["X","ALUo","INen","Fi"]
            add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,setA,changeREG])

def add_16bit_MATHS():
    word_Pairs=["AB","r0r1","r2r3","r4r5"]
    ALU_ARITHMETIC = [("ADD",0),("SUB",1),("CMP",2)]#,("ADDC",8),("SUBC",9), ("CMPC",10)]

    # ADDC = 0b 1 0 0 0
    for p_indexin,pair_in in enumerate(word_Pairs):
        reg_i = p_indexin*2
        i2 = 1 if reg_i&4 else 0
        i1 = 1 if reg_i&2 else 0
        i0 = 0

        if pair_in!="AB":
            # INCC 0b1100
            # ADDC 0b0100
            
            # 0b i2 i1 i2 i1 1 1 0 0
            # INC 0b0011
            # inc r0r1  0b 0  1  0  1  1   1 0  0

            addr = (i2<<7) | (i1<<6) | (i2<<5) | (i1<<4) | (0b1100) 
            valid = [addr]
            new_ins = "INC "+pair_in # INCrement register pair with carry_in
            # i.e. INCC r0r1
            # A = r1 (i0=1)
            # B = 1
            # ALU = 0b1100, ALU out = r1, ADD (duplication of ADD in terms of control signals)
            # A = r0 (i0=0, X-signal asserted)
            # B = 0
            # ALU = 0b0100 (ADDC), ALU out = r0, X-signal asserted, a3=0, i0=0
            add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["OUTen","Ai"],["Bi","X"],["ALUo","INen","Fi"],["OUTen","Ai","X"],["Bi"],["ALUo","INen","X","Fi"]])
        
def add_16bit_MOV():
    # 0b i2 i1 o2 o1 o0 i0 x x
    word_Pairs=["AB","r0r1","r2r3","r4r5"]
    
    for p_indexin,pair_in in enumerate(word_Pairs):
        reg_i = p_indexin*2
        for p_indexout,pair_out in enumerate(word_Pairs):
            reg_o = p_indexout*2

            i2 = 1 if reg_i&4 else 0
            i1 = 1 if reg_i&2 else 0
            i0 = 0

            o2 = 1 if reg_o&4 else 0
            o1 = 1 if reg_o&2 else 0
            o0 = 0
            
            addr = (i2<<7)|(i1<<6)|(o2<<5)|(o1<<4)|(o0<<3)|(i0<<2)

            valid = [x for x in range(0,256) if (x&0b11111100)==addr] # need to match output and input pair addresses by default
            
            if pair_in!=pair_out:
                new_ins ="MOV "+pair_in+","+pair_out
                if pair_in=="AB":
                    setiH = ["OUTen","Ai"]
                    setiL = ["OUTen","Bi","X"]
                    valid = [x for x in range(0,256) if (x&0b11000100)==((i2<<7)|(i1<<6)|(i0<<2))] # only need to match output register 
                else:
                    setiH = ["OUTen","INen"]
                    setiL = ["OUTen","INen","X"] # X signal sets i0 and o0 = 1
                    if pair_out=="AB":
                        setiH = ["Ao","INen"] # A is high register, use Aout signal
                        sitiL = ["OUTen","INen","X"] # set o0 = io = 1 to access lower byte register (i.e. B, r1, r3 and r5)
                    
                add_instruction(new_ins,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,setiL,setiH])
            else:
                addr = (i2<<7)|(i1<<6)|(i0<<2)
                valid = [x for x in range(0,256) if (x&0b11000100)==addr] # only need to match input register pair for this/these instructions
                if pair_in=="AB":
                    setiH = ["Ro","Ai","PCinc"]
                    setiL = ["Ro","Bi","PCinc"]
                    valid = [x for x in range(0,256)] # instruction can go literally anywhere
                else:
                    setiH = ["Ro","INen","PCinc"]
                    setiL = ["Ro","INen","X","PCinc"]
                
                add_instruction("MOV "+pair_in+",0x@@@@",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],setiH,["PCo","MARi"],setiL])

        # Store 0x@@ in B register, set the address to that contained in register pair (AB won't work!), put B into memory address
        if pair_in!="AB":
            # reg_i is either 0 (AB), 2 (r0r1), 4 (r2r3) or 6 (r4r5), i.e. always even, o0=0 (not i0, because output bits are set to read register pair).
            addr = (reg_i<<3) # put reg_i into reg_out position
            valid = [x for x in range(0,256) if x&0b00111000==addr] # just match output register for these instructions
        
            storeH = ["OUTen","T_EN"] # T-reg: Save (input) from LOW bus
            setL = ["OUTen","T_HL","T_IO","T_EN","MARi","X"] # X signal sets i0 and o0 =# put . Output T-reg to HIGH bus
            add_instruction("MOV ["+pair_in+"],0x@@",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","Ai","PCinc"],storeH,setL,["Ao","Ri"]])   
            add_instruction("MOV ["+pair_in+"],A", pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,storeH,setL,["Ao","Ri"]])
            add_instruction("MOV A,["+pair_in+"]",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,storeH,setL,["Ro","Ai"]])
        

def get3bits(a):
    a2 = 1 if a&4 else 0
    a1 = 1 if a&2 else 0
    a0 = 1 if a&1 else 0

    return (a2,a1,a0)

def add_8bit_MOV():

    #reg_names = ["A","B","r0","r1","r2","r3","r4","r5"]
    for reg_in_index,reg_in in enumerate(reg_names):
        for reg_out_index,reg_out in enumerate(reg_names):
            i2,i1,i0 = get3bits(reg_in_index)
            o2,o1,o0 = get3bits(reg_out_index)
            
            if reg_in!=reg_out:
                #0b i2 i1 o2 o1 o0 i0 x x
                #also: 0b i2 i1 o2 o1 !o0 !i0 x  x (assert X-signal during transfer)

                MOV=[]
                addr = (i2<<7) | (i1<<6) | (o2<<5) | (o1<<4) | (o0<<3) | (i0<<2)
                
                if reg_in=="A":
                    MOV.append("Ai")
                    valid = [x for x in range(0,256) if x&0b00111000 == (reg_out_index<<3)] # Don't need to set input register address
                elif reg_in=="B":
                    MOV.append("Bi")
                    valid = [x for x in range(0,256) if x&0b00111000 == (reg_out_index<<3)] # Don't need to set input register address
                    if reg_out=="A":
                        valid = [x for x in range(0,256)] # Don't need to set input OR output address!
                else:
                    MOV.append("INen")
                    valid = [x for x in range(0,256) if x&0b11111100 == addr]
                    if reg_out=="A":
                        valid = [x for x in range(0,256) if x&0b11000100 == ((i2<<7)|(i1<<6)|(i0<<2))] # only consider input register address

                # Just handle output signals here - the valid address settings are set above for all cases
                if reg_out=="A":
                    MOV.append("Ao")
                else:
                    MOV.append("OUTen")
                
                
                pos=add_instruction("MOV "+reg_in+","+reg_out,pos=None,addresses=valid,quiet=True,microcode_lines=[FETCH0,FETCH1,MOV])
                if pos==-1:
                    # Try these positions, invert i0 and o0 bits, then assert X-signal
                    addr = (i2<<7) | (i1<<6) | (o2<<5) | (o1<<4) | ((1-o0)<<3) | ((1-i0)<<2)

                    reg_out_index = (o2<<2)|(o1<<1)|((1-o0)<<0)
                    
                    if reg_in=="A":
                        valid = [x for x in range(0,256) if x&0b00111000 == (reg_out_index<<3)] # Don't need to set input register address
                    elif reg_in=="B":
                        valid = [x for x in range(0,256) if x&0b00111000 == (reg_out_index<<3)] # Don't need to set input register address
                        if reg_out=="A":
                            valid = [x for x in range(0,256)] # Don't need to set input OR output address!
                    else:
                        valid = [x for x in range(0,256) if x&0b11111100 == addr]
                        if reg_out=="A":
                            valid = [x for x in range(0,256) if x&0b11000100 == ((i2<<7)|(i1<<6)|((1-i0)<<2))] # only consider input register address
                    
                    MOV.append("X")
                    add_instruction("MOV "+reg_in+","+reg_out,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,MOV])
    
def add_8bit_MOV_misc():
    #reg_names = ["A","B","r0","r1","r2","r3","r4","r5"]

    # REGISTERS ARE WRITTEN
    for reg_in_index,reg_in in enumerate(reg_names):
        i2,i1,i0 = get3bits(reg_in_index)

        # MOV reg, 0x@@
        # MOV reg, [0x@@]
        # MOV reg, [0x@@@@] ; ? is this useful? already implemented with register pair addressing
        if reg_in=="A":
            valid = [a for a in range(0,256)]
            changeREG="Ai"
        elif reg_in=="B":
            valid = [a for a in range(0,256)]
            changeREG="Bi"
        else:
            valid = [a for a in range(0,256) if (a&0b11000100)==((i2<<7)|(i1<<6)|(i0<<2))]
            changeREG="INen"
        add_instruction("MOV "+reg_in+",0x@@",pos=None, addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro",changeREG,"PCinc"]])
                                                                                                                    # With nothing on the HIGH databus, ZP address appears
        add_instruction("MOV "+reg_in+",[0x@@]",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","PCinc","MARi"],["Ro",changeREG]])
        add_instruction("MOV "+reg_in+",[0x@@@@]",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","T_EN","PCinc"],["PCo","MARi"],["Ro","T_HL","T_IO","T_EN","MARi","PCinc"],["Ro",changeREG]])
        add_instruction("POP "+reg_in,pos=None, addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro",changeREG,"SPinc"]])

    # REGISTERS ARE READ
    for reg_out_index,reg_out in enumerate(reg_names):
        o2,o1,o0 = get3bits(reg_out_index)

        if reg_out=="A":
            valid = [a for a in range(0,256)]
            readREG="Ao"
        else:
            valid = [a for a in range(0,256) if (a&0b00111000)==(reg_out_index<<3)]
            readREG="OUTen"
        
        add_instruction("PUSH "+reg_out,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPdec"],["SPo","MARi"],[readREG,"Ri"]])
        add_instruction("MOV [0x@@],"+reg_out,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","PCinc","MARi"],["Ri",readREG]])
        add_instruction("MOV [0x@@@@],"+reg_out,pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","T_EN","PCinc"],["PCo","MARi"],["Ro","T_HL","T_IO","T_EN","MARi","PCinc"],["Ri",readREG]])

        # not that useful...?
        if reg_out=="A":
#            add_instruction("PUSH "+reg_out+"-2",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPdec"],["SPdec"],["SPdec"],["SPo","MARi","SPinc"],[readREG,"Ri","SPinc"],["SPinc"]])
#            add_instruction("POP "+reg_out+"-2",pos=None, addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPdec"],["SPo","MARi"],["Ro","Ai","SPinc"]])
            push8bit = add_instruction("PUSH 0x@@",pos=None,addresses=[a for a in range(0,256)],microcode_lines=[FETCH0,FETCH1,["SPdec","PCo","MARi"],["Ro","PCinc","T_EN"],["SPo","MARi"],["Ri","T_EN","T_IO"]])
            #spare = add_instruction("SPARE",pos=None,addresses=[a for a in range(0,256)],microcode_lines=[FETCH0,FETCH1])
            add_instruction("POP T",pos=None,addresses=[a for a in range(0,256)],microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro","T_EN","SPinc"]]) # pop return address into T register. 
            #print("spare at:",spare)
    
def add_FLAGs():
    #           PUSH F
#           POP F
#           MOV A, F
    valid = [a for a in range(0,256)]
    add_instruction("MOV A,F",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["Fo","Ai"]])
    add_instruction("PUSH F",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPdec"],["SPo","MARi"],["Fo","Ri"]])
    add_instruction("POP F",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro","Fi","SPinc","T_IO"]])

def add_JMPs():
    valid = [a for a in range(0,256)]
    
    first_slot=None
    for i in range(0,255):
        if instruction_set[i]=="" and instruction_set[i+1]=="":
            first_slot=i
            break
    push=add_instruction("PUSH_PC+1",pos=first_slot,microcode_lines=[FETCH0,FETCH1,["SPdec"],["SPo","MARi"],["PCo","Ri","SPdec","T_EN","T_HL"],["SPo","MARi"],["T_EN","T_IO","Ri"]])
                                                                                                                                            # Output 0x@@ (transfer reg) --> low bus
                                                                                    # RAM --> Transfer reg (via low bus)... then: Transfer reg --> High bus OUTPUT 
    pos=add_instruction("INT",pos=push+1,microcode_lines=[FETCH0,FETCH1,["MARi"],["Ro","T_EN"],["MARi","X"],["Ro","T_EN","T_HL","T_IO","PCi"]])
    # INT~, the tilde tells the instruction to add a padding byte to the instruction so that (what? RETI behaves correctly?) 
    print("PUSH PC+1 at:",push,hex(push),bin(push)) 
    print("INT at:",pos,hex(pos),bin(pos))
    
    # Z C m m m I I I I I I I I
    # Jump conditions ZC:
    # 0 - Z=0, C=0,# jg, jge, jne,jnz
    # 1 - Z=0, C=1,# jl, jle, jne,jnz
    # 2 - Z=1, C=0 # je, jge, jle,jz
    # 3 - Z=1, C=1 # jz

    ZC=[""]*4
    ZC[0] = ["JG","JGE","JNE","JNZ","JMP","CALL","JC"]
    ZC[1] = ["JL","JLE","JNE","JNZ","JMP","CALL","JNC"]
    ZC[2] = ["JE","JGE","JLE","JZ","JMP","CALL","JC"]
    ZC[3] = ["JZ","JMP","CALL","JNC"]
    # Call is a special case, we need to put PC onto stack first!
    JMPs = ["JZ","JNZ","JE","JNE","JG","JGE","JL","JLE","JMP","JC","JNC"]

    no_jump = [FETCH0,FETCH1,["PCinc"],["PCinc"]]
    jump_code = [FETCH0,FETCH1,["PCo","MARi"],["Ro","T_EN","PCinc"],["PCo","MARi"],["Ro","T_HL","T_IO","T_EN","PCi"]]
    for j in JMPs:
        ins = j+" 0x@@@@"
        JMP_pos=add_instruction(ins,pos=None,addresses=valid)
        
        define_microcode(JMP_pos,jump_code if j in ZC[0] else no_jump,ZC=0)
        define_microcode(JMP_pos,jump_code if j in ZC[1] else no_jump,ZC=1)
        define_microcode(JMP_pos,jump_code if j in ZC[2] else no_jump,ZC=2)
        define_microcode(JMP_pos,jump_code if j in ZC[3] else no_jump,ZC=3)

    # CALL is: PUSH PC (SP into MAR, write PC), JMP to @@@@

    #PUSH PC+3: stores LOW byte of PC on stack first, followed by HIGH byte of PC
    #add_instruction("INC PC",pos=None,addresses=valid,microcode_lines=[["PCo","MARi","PCinc"],["Ro","Ii","PCinc"]]) # Gets Instruction and does double pointer increment
    
    #functions are page aligned...
    
    no_call=[FETCH0,FETCH1,["SPinc","PCinc"],["SPinc","PCinc"]] # Didn't call function so need to undo effect of pushing the return address onto the stack and need to increment PC
    ##call_code=[FETCH0,FETCH1,["PCo","MARi"],["Ro","T_EN"],["X","T_EN","T_HL","T_IO","PCi"]] #[PC]=T_reg, PC = [PC]:00
    call_code=[FETCH0,FETCH1,["PCo","MARi"],["Ro","T_EN","PCinc"],["PCo","MARi"],["Ro","T_HL","T_IO","T_EN","PCi"]] # PC=[PC][PC+1]
    
     #         PC PC+1
     # CALL_OP:HI:LO
     
    for c in CALLS:
        if c=="CALL":
            ins = c+" 0x@@@@"
            jsearch = "CALL"
        else:
            jsearch = "J"+c.split("_")[1]
            ins = c+" 0x@@@@"
        
        call_pos = add_instruction(""+ins,pos=None,addresses=valid)#,microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","T_EN"],["X","T_EN","T_HL","T_IO","PCi"]])#["Ro","T_EN","PCinc"],["PCo","MARi"],["Ro","T_HL","T_IO","T_EN","PCi"]])

        for condition in range(0,4):
            define_microcode(call_pos,call_code if jsearch in ZC[condition] else no_call,ZC=condition)
     
    #add_instruction("RET",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro","T_EN","SPinc"],["SPo","MARi"],["Ro","T_EN","T_HL","T_IO","PCi","SPinc"],["PCinc"],["PCinc"]])
    add_instruction("RET",pos=None,addresses=valid,microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro","T_EN","T_HL","T_IO","PCi","SPinc"],["PCinc"],["PCinc"],["PCinc"]])

def add_UART():
    # add UART_out to reg_IN
    #reg_names_IN = ["_Uin","_Uout","r0","r1","r2","r3","r4","r5"]
    # 0b i2 i1 o2 o1 o0 i0 x x
    # MOV U,A = 0b000000xx ; out = 0b000 (A), in = 0b000 (Uin)

    MASK_IN = 0b11000100
    MASK_OUT = 0b00111000
    Ureg_mask = (0<<7)|(0<<6)|(1<<2) # Uout

    reg_names_UART = ["A","B"]#,"r0","r1","r2","r3","r4","r5"]
    for reg_index, reg in enumerate(reg_names_UART):
        new_ins = "MOV U,"+reg

        if reg=="A":
            # MOV U,REG 0b0 0 x x x 0 x x # Uin = 0b000
            # Ao handles the output (not OUTen), and Uin is at address 0b000 of the input address
            add_instruction(new_ins,pos=None,addresses=[x for x in range(0,256) if x&MASK_IN==0],microcode_lines=[FETCH0,FETCH1,["Ao","INen"]])
        else:
            # MOV U,REG 0b0 0 o2 o1 o0 0 x x # Uin = 0b000
            add_instruction(new_ins,pos=None,addresses=[x for x in range(0,256) if x&(MASK_IN|MASK_OUT)==(reg_index<<3)],microcode_lines=[FETCH0,FETCH1,["OUTen","INen"]])
        
    add_instruction("MOV U,0x@@",pos=None,addresses=[x for x in range(0,256) if x&MASK_IN==0],microcode_lines=[FETCH0,FETCH1,["PCo","MARi"],["Ro","INen","PCinc"]])
    # MOV A,U = 0b00xxx1xx ; out = xxx (Ai), in = 0b001 (Uout)
    add_instruction("MOV A,U",pos=None,addresses=[x for x in range(0,256) if x&MASK_IN==Ureg_mask],microcode_lines=[FETCH0,FETCH1,["Ai","INen"]])
    add_instruction("MOV B,U",pos=None,addresses=[x for x in range(0,256) if x&MASK_IN==Ureg_mask],microcode_lines=[FETCH0,FETCH1,["Bi","INen"]])
    

def add_misc():
    add_instruction("NOP",pos=255,microcode_lines=[FETCH0,FETCH1])
    add_instruction("HALT",pos=None,addresses=[x for x in range(0,256)],microcode_lines=[FETCH0,FETCH1,["HALT"]])
    ##add_instruction("PUSH PC",252)#pos=None,addresses=range(0,256))
    ##add_instruction("POP PC",253)#pos=None,addresses=range(0,256))
    ##add_instruction("HALT",254)
    ##add_instruction("NOP",255,microcode_lines=[FETCH0,FETCH1])

def find_instruction(ins_str):
    for op,ins in enumerate(instruction_str.split("#")):
        if ins_str==ins:
            return "0x{:02x}".format(op)
    return None

MAX_MICRO_LINE_BITS = 3 # 3 = 2**3, 3-bit microcode lines
MAX_MICRO_LINES = 2**MAX_MICRO_LINE_BITS

signals={}

# ADDRESS_SPACE = 2**(8+2+3) #256 instructions, Z, C and 3-bit microcode counter
# Z C m m m I I I I I I I I
microcode = [[""]*MAX_MICRO_LINES for m in range(256*4)]

# Need to check all the active-low status of these signals in reality

# First set of control signals lets us fetch an instruction and out from ALU (but not set flags)
define_signal("Ai",True) #0
define_signal("ALUo",True)#1
define_signal("Ii",True) # 2
define_signal("PCo",True) #3
define_signal("PCinc")#4
define_signal("MARi") # 5
define_signal("Ro") # 6 - RAM out, memory read
define_signal("MC_reset") # 7 - microcode counter reset

# Second set of control signals lets us interface with the higher 8 bits of 16-bit bus, write to memory, set flags and use the stack
define_signal("T_HL") # 8 # Transfer register High/Low.  Need to check these all make sense
define_signal("T_IO") # 9 # Transfer register In/Out.  Need to check these all make sense T_IO = LOW means INPUT, T_IO = HIGH means OUTPUT
define_signal("T_EN") # 10 # Transfer register enable.
define_signal("Ri")   # 11 # Memory write
define_signal("Fi",True)    # 12
define_signal("SPdec")# 13
define_signal("SPinc")# 14
define_signal("Bi",True) #15

# 3rd set expands register set (r0-5), X-signal and allows JMPing with PCi
define_signal("PCi") #
define_signal("Ao",True)
define_signal("OUTen",True) # enable register-out demux
define_signal("INen",True) # enable register-in demux
define_signal("X") # X-signal, does various XOR manipulation of o0, a3 and i0
define_signal("Fo", True) # FLAG register out
define_signal("HALT")
define_signal("SPo",True)

FETCH0 = ["PCo","MARi"]
FETCH1 = ["Ro","Ii","PCinc"]

# Notes:
# Need to handle T_HL and T_IO as active lows so are compatible with PCB

#index in instructions is opcode machine code
# ' ' indicates the end of the instruction and start of (optional) parameters
# '@' means digit 0-9
# 'A' means A register
# 'B' means B register
# ',' separates arguments
# '~' add byte padding to machine code
# '#' means end of instruction

# Can should/this be a string in continuous memory? Yes that would be more memory friendly

instruction_set = [""]*256 # 256 instructions to be defined

# Instruction format:
# 0b i2 i1 o2 o1 x1 a2 a1 a0

# what if:
# a3 = XOR(X-sig,x1)
# o0 = XOR(X-sig,x1) = a3
# i0 = XOR(X-sig,a2)

reg_names_IN = ["U","_Uout","r0","r1","r2","r3","r4","r5"]
reg_names=["A","B","r0","r1","r2","r3","r4","r5"]

reg_names_OUT = ["CLEAR INT STATUS","B","r0","r1","r2","r3","r4","r5"]

ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A","ADDC A,B","SUBC A,B","CMPC A,B","NOT A","SHL A","XOR A,B","NAND A,B","OR A,B","INC A","AND A,B", "NOR A,B", "RCL A"]
CALLS=["CALL_Z","CALL_NZ","CALL_E","CALL_NE","CALL_G","CALL_GE","CALL_L","CALL_LE","CALL","CALL_C","CALL_NC"]

#add_UART()
add_ALU_inc_dec()
add_ALU_ARITHMETIC()
add_UART()

add_16bit_MOV()

add_16bit_MATHS()

add_8bit_MOV()

# OUT_EN in the zeroth position is used to clear the "in interrupt" function.
ret_valid = [x for x in range(0,256) if x&0b00111000==0b000000]
add_instruction("RETI",pos=None,addresses=ret_valid,microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro","T_EN","SPinc"],["SPo","MARi"],["Ro","T_EN","T_HL","T_IO","PCi","SPinc"],["PCinc","OUTen"]])
#add_instruction("RETI",pos=None,addresses=ret_valid,microcode_lines=[FETCH0,FETCH1,["SPo","MARi"],["Ro","T_EN","T_HL","T_IO","PCi","SPinc"],["PCinc","OUTen"]])

add_8bit_MOV_misc()

add_ALU_LOGIC()

add_carry_set_clear() # setc replaced with customasm (CMPC A,0)

add_FLAGs()
add_JMPs()

add_misc()

instruction_str = ""

output_type = 0# 0 = No output, 1 = customasm CPU definition, 2 = instruction property table, 3 = instruction_str for ASM interpreter
headers=["Instruction","Opcode","PC change","Register change"]
instruction_table = []

if output_type==1:
    print("#ruledef")
    print("{")
elif output_type==2:
    pass

total_ins=0
custom_asm=[]
free_ins=[]

for op,ins in enumerate(instruction_set):
    instruction_str+=ins+"#"

    if ins!="":
        if output_type==1: custom_asm.append(customasm(ins,op))
        if output_type==2: instruction_table.append(info_table(ins,op))
        total_ins+=1
    else:
        free_ins.append(op)
    
    if ins!="":
        zc_0 = microcode[op][0]
        zc_1 = microcode[op+256][0]
        zc_2 = microcode[op+512][0]
        zc_3 = microcode[op+768][0]
        if zc_0 == "" or zc_1 == "" or zc_2 == "" or zc_3 == "":
            print("ERROR: Microcode not fully defined for opcode:",op,", instruction:",ins)

def not_8bit(a):
    result = 0
    for i in range(0,8):
        bit = 0 if (1<<i)&a else (1<<i)
        result |= bit
    return result

def xor_8bit(a,b):
    result = 0
    for i in range(0,8):
        result |= ((1<<i)&a) ^ ((1<<i)&b)
    #print(a,b,result)
    return result

if output_type==1:# append other instructions for customasm
    find_subc = find_instruction("CMP A,0x@@")
    custom_asm.append("setc => "+find_subc+"00")
                      
    find_and = find_instruction("AND A,0x@@")
    find_or = find_instruction("OR A,0x@@")
    find_xor = find_instruction("XOR A,0x@@")
    #ruledef = ins+" => "+hex(op) + post
    for b in range(0,8):
        ANDbitmask = "{:02x}".format(not_8bit(1<<b))
        ORbitmask = "{:02x}".format((1<<b))
        XORbitmask = "{:02x}".format((1<<b))

        # Bonus instructions using existing instructions :)
        custom_asm.append("cbi a,"+str(b)+" => "+find_and+ANDbitmask)
        custom_asm.append("sbi a,"+str(b)+" => "+find_or+ORbitmask)
        custom_asm.append("tbi a,"+str(b)+" => "+find_xor+XORbitmask)

    find_pushpc = find_instruction("PUSH_PC+1")
    for c in CALLS:
        if c=="CALL":
            find_call = find_instruction("CALL 0x@@@@")[2:]
            c+=" "
        else:
            find_call = find_instruction(""+c+",0x@@@@")[2:] # this might be wrong now, but we're not using customasm anyway
            c+=","
        #CALL Z,{addr16: u16} => {assert((addr16[7:0]==0)), 0xdfe2 @addr16[15:8]}
	 
        custom_asm.append("_"+c+"{addr16: u16} => {assert((addr16[7:0]==0)),"+find_pushpc+find_call+" @addr16[15:8]}")

    find_int = find_instruction("INT~")
    custom_asm.append("_INT => "+find_int+"00")
    for l in sorted(custom_asm):
        print("\t",l)
    print("}")
    print("Number of customasm instructions:",len(custom_asm))
    
if output_type==2:
    # Bit of processing
    for i,line in enumerate(instruction_table):
        line=line.split('\t')
        line = [x for x in line if x!='']
        instruction_table[i] = line

    instruction_table = sorted(instruction_table, key=lambda ins: ins[2])
    for line in instruction_table:
        s=""
        if len(line[2])<8: line[2]+='\t'
        if len(line[3])<8: line[3]+='\t'
        
        if ',' in line[5]:
            regs = line[5].split(',')
            regs = sorted(regs)
            line[5] = ",".join(regs)

        if len(line[5])<8: line[5]+='\t'
        for element in line:
            s += element+'\t'
        print(s)
    print("Total instructions=",total_ins)
if output_type==3: print(instruction_str, len(instruction_str))

# Put "NOP" into unfilled instructions:
for i in range(0,256*4):
    if microcode[i][0]=="":
        define_microcode(i,[FETCH0,FETCH1,["MC_reset"]]) # NOP

# ADDRESS_SPACE = 2**(8+2+3) #256 instructions, Z, C and 3-bit microcode counter
# Z C m m m I I I I I I I I
if __name__=="__main__":
    write_EEPROM = True # Write EEPROM bytearray to file
else:
    write_EEPROM = False

def write_EEPROM_block(EEPROM_BYTE,textmode=False):
    # Which byte of the control word is getting written to the EEPROM? EEPROM_BYTE either 0, 1 or 2 for 24 control signals
    # bits 0-7: EEPROM_BYTE = 0
    # bits 15-8: EEPROM_BYTE = 1
    # bits 23-16: EEPROM_BYTE = 2

    if textmode:
        f = open("control_EEPROM"+str(EEPROM_BYTE)+".txt","wb")
    else:
        f = open("control_EEPROM"+str(EEPROM_BYTE)+".py","w")
        f.write("control"+str(EEPROM_BYTE)+"=")

    writearray = bytearray(2**(8+2+3))

    for addr in range(0,2**(8+2+3)):
        ins = addr & 0xFF
        mmm = (addr >> 8) & 0x07
        ZC = (addr>>11) & 0x03
        
        control_word = get_microcode_int(microcode[ins+(ZC<<8)][mmm])
        control_byte = (control_word>>(8*EEPROM_BYTE)) & 0xFF
        
        writearray[addr] = control_byte
            
##        if EEPROM_BYTE==1:
##            print(addr,ins,mmm,ZC,bin(control_word),bin(control_byte))
    if textmode:
        f.write(writearray)
        print("Wrote...'control_EEPROM"+str(EEPROM_BYTE)+".txt'")
    else:
        f.write(str(writearray))
        print("Wrote...'control_EEPROM"+str(EEPROM_BYTE)+".py'")     
    f.close()

print("Free instruction slots at:")
for i in free_ins:
    # 0b 7  6  5  4  3  2  1  0
    # 0b i2 i1 o2 o1 o0 i0 a1 a0
    i2 = 1 if i&(1<<7) else 0
    i1 = 1 if i&(1<<6) else 0
    o2 = 1 if i&(1<<5) else 0
    o1 = 1 if i&(1<<4) else 0
    o0 = 1 if i&(1<<3) else 0
    i0 = 1 if i&(1<<2) else 0
    a1 = 1 if i&(1<<1) else 0
    a0 = 1 if i&(1<<0) else 0
    
    in_reg = (i2<<2)|(i1<<1)|i0
    out_reg = (o2<<2)|(o1<<1)|o0
    in_regX = (i2<<2)|(i1<<1)|(1-i0)
    out_regX = (o2<<2)|(o1<<1)|(1-o0)

    alu = (o2<<3)|(i0<<2)|(a1<<1)|(a0<<0)
    aluX = ((1-o2)<<3)|(i0<<2)|(a1<<1)|(a0<<0)
#ALU_INSTRUCTIONS    
    print("Op=",i,bin(i),"in_reg=",reg_names_IN[in_reg],"out_reg=",reg_names_OUT[out_reg],"in_regX=",reg_names_IN[in_regX],"out_regX=",reg_names_OUT[out_regX],"ALU=",ALU_INSTRUCTIONS[alu],"ALUX=",ALU_INSTRUCTIONS[aluX])
if write_EEPROM:
    write_EEPROM_block(0,textmode=True)
    write_EEPROM_block(1,textmode=True)
    write_EEPROM_block(2,textmode=True)
    
