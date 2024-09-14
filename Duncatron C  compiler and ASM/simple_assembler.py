import re
import CPUSimulator.define_instructions

class Assembler:
    ADDRESS_DEFINITION = 256
    LABEL_DEFINITION = 257

    MEMORY_LABEL = 258
    
    DATABYTES = 259
    DATASTRING = 260
    DATAWORDS = 261
    
    def __init__(self,filename,memory,text):
        self.lines = []
        self.memory = memory
        self.maxPOS = 0
        self.instruction_str = CPUSimulator.define_instructions.instruction_str
        if filename!=None:
            self.read_and_clean_file(filename)
        else:
            self.read_and_clean_text(text)

        self.asmfilename = filename
        self.asmregex = []
        self.labels = {} # Dictionary of labels and their memory addresses
        self.labelref = []

        self.lookupASM = []
     
    def read_and_clean_text(self,text):
        print("Warnng, this doesn't implement safe ; and : handling, unlike read_and_clean_file")
        for line in text.split("\n"):
            if ";" in line:
                line = line[:line.find(";")]
            self.lines.append(line.strip())
    
    def read_and_clean_file(self,filename):
        with open(filename) as file:
            for line in file:
                # Find first ; character that isn't in a string
                semi_pos = self.find_char(line,";")
                if semi_pos!=None:
                    line = line[:semi_pos]

                # Find colons not in a string
                colon_pos = self.find_char(line,":")
                if colon_pos!=None:
                    line_split0 = line[:colon_pos+1].strip()
                    line_split1 = line[colon_pos+1:].strip()
                    self.lines.append(line_split0)
                    if len(line_split1)>0:
                        self.lines.append(line_split1)
                        
                else: # commit line
                    self.lines.append(line.strip())
    def find_char(self,string,char):
        # mov A,B ; this should be ignored
        # dstr 'mov A,B ; this shouldn't be ignored'
        # dstr 'mov A,B ; this shouldn't be ignored' ; this should be!

        # label0:
        # dstr 'commands: /h help'
        instring = 0
        for pos,a in enumerate(string):
            if a==char and instring==0:
                    return pos
            if a=="'":
                instring=1-instring
        return None
    
    def add_label(self,newlabel,address):
        if newlabel in self.labels:
            print("ERROR: Label '"+newlabel+"' already declared!")
            return False
        self.labels[newlabel]=address
        return True

    def add_call_or_jmp_reference(self, prelabel, label, address,offset,pureData=False):
        # 'address' is the memory address of the position in code (not the label address, we don't know that necessarily yet)
        if label in self.labels:            
            myline = prelabel+"0x"+format(self.labels[label], '04x')
        else:
            self.labelref.append((label,address+offset)) # record where the call/jmp label instruction was to backfill address later
            myline = prelabel+"0x0000"

        if pureData:
            number = int(myline,16)
            newasm = [(number>>8)&0xff,number&0xff]
        else:
            newasm = self.machinecode(myline) # add dummy address as padding for now

        for byte in newasm:
            self.write_memory(address,byte)#self.memory[pointer]=byte
            address+=1

        return address

    def backfill_references(self):
        for reference in self.labelref:
            label,address = reference
            if not label in self.labels:
                print("ERROR. "+label+" referenced but not declared")
                return False
            else:
                label_address = self.labels[label]
                self.write_memory(address,label_address>>8)#self.memory[address] = label_address>>8
                self.write_memory(address+1,label_address&0xFF)#self.memory[address+1] = label_address & 0xFF
        return True
    
    def assemble(self):
        print("Making regex...")
        if not self.make_regex(): return False
        print("Regex complete")
        POPT_opcode = self.machinecode("POP T")[0]
        RET_opcode = self.machinecode("RET")[0]
        INT_opcode = self.machinecode("INT")[0]
        RETI_opcode = self.machinecode("RETI")[0]
        PUSHPC_opcode = self.machinecode("PUSH_PC+1")[0]
        
        pointer = 0
        for line_number,line in enumerate(self.lines):
            cleaned_line = self.clean_line(line)
            if cleaned_line==False:
                print("Error processing line #"+str(line_number)+": "+line)
                return False

            asm = self.machinecode(cleaned_line)
            print(line_number)
            if asm:
                opcode = asm[0]

                # try to flag some likely sources of programming bugs
                
                if opcode==RET_opcode and was_POPT==False:
                    print("RET must be preceeded by 'POP T', line number:",line_number)
                    return False
                if opcode==INT_opcode and was_PUSHPC==False:
                    print("INT must be preceeded by 'PUSH_PC+1', line number:", line_number)
##                if opcode in CALL_opcodes and was_PUSHPC==False:
                if len(cleaned_line)>=4: ## Detect CALLs this way
                    if cleaned_line[:4].upper()=="CALL" and was_PUSHPC==False:
                        print("CALLs must be preceeded by 'PUSH_PC+1', line number:", line_number)
                        return False
                if opcode==RETI_opcode and was_POPT:
                    print("RETI should NOT be preceeded by 'POP T', line number:", line_number)
                
                was_POPT = (opcode==POPT_opcode)
                was_PUSHPC = (opcode==PUSHPC_opcode)
                
                if opcode<256: # a normal instruction, write into memory
                    for byte in asm:
                        self.write_memory(pointer,byte)#self.memory[pointer]=byte
                        pointer+=1
                elif opcode==self.ADDRESS_DEFINITION: # other behaviour specified
                    if asm[1]<pointer:
                        print("ERROR. Memory label ("+hex(asm[1])+") on line number",line_number,"must be declared at higher address than current pointer ("+hex(pointer)+")")
                        return False
                    pointer=asm[1]
                elif opcode==self.LABEL_DEFINITION:
                    if not self.add_label(asm[1],pointer):
                        return False

                elif opcode == self.MEMORY_LABEL:
                    pointer = self.add_call_or_jmp_reference(asm[1],asm[2],pointer,1,pureData=False)
                elif opcode == self.DATABYTES or opcode == self.DATAWORDS:
                    #print(asm[1],type(asm[1]))
                    asm[1]=str(asm[1])
                    
                    if "," in asm[1]:
                        bytelist = asm[1].split(",")
                    else:
                        bytelist = [str(asm[1])]
                   
                    for databyte in bytelist:
                        int_bytelist,status = self.process_databyte(databyte.strip(),opcode)
                        if status==0:
                            print("Could not process data byte/word '"+databyte+"' at line number:",line_number)
                            return False
                        elif status==1:
                            for byte in int_bytelist:
                                self.write_memory(pointer,byte)
                                #print("Writing:",pointer,byte)
                                pointer+=1
                        elif status==2:
                            # treat as a memory label
                            pointer = self.add_call_or_jmp_reference("",int_bytelist,pointer,0,pureData=True)
                elif opcode == self.DATASTRING:
                    datastr = self.process_datastring(asm[1])
                    for character in datastr:
                        self.write_memory(pointer,ord(character))#self.memory[pointer]=ord(character)
                        pointer+=1
                    self.write_memory(pointer,0)#self.memory[pointer]=0 # Add zero terminator automatically
                    pointer+=1
                else:
                    print("Don't know how to process opcode! OPCODE=",opcode)
                    return False
            elif asm==False:
                print("Failed to generate machine code on line:",line_number,":",line)
                return False
        return self.backfill_references()

    def write_memory(self,position,byte):
        self.memory[position]=byte
        if self.maxPOS<position:
            self.maxPOS=position

    def process_datastring(self, data_str):
        # Check for ',' not in quotation marks and concatenate, return string
        in_quote = 1 # Inside a quote mark by default
        return_str = ""
        for char in data_str:
            if char=="'":
                in_quote = 1-in_quote
                if in_quote: # Just started a new string so terminate the old one
                    return_str+=chr(0)
            else:
                if in_quote:
                    return_str+=char # Only add characters in quotes
        return return_str
    
    def process_databyte(self, data_byte, data_type):
        # hex byte
        if data_type==self.DATABYTES:
            hex_regex = "^0x([0-9A-Fa-f]{2})$"
        elif data_type==self.DATAWORDS:
            hex_regex = "^0x([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})$"
        else:
            print("ERROR! data_type not recognise")
            return (False,0)
    
        match = re.match(hex_regex,data_byte,re.IGNORECASE)
        if match:
            byte_list = [int(m,16) for m in match.groups()]
            return (byte_list,1)#int(match.group(0),16)
        
        # integer (base-10)  
        int_regex = "^([0-9]*)$"
        match = re.match(int_regex,data_byte,re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if data_type==self.DATABYTES:
                byte_list = [num]
            elif data_type==self.DATAWORDS:
                byte_list = [(num>>8)&0xff,num&0xff]
            return(byte_list,1)

        # array, int size
        array_int = "^\[([0-9]*)\]$" # i.e [33]
        match = re.match(array_int,data_byte,re.IGNORECASE)
        if match:
            array_size = int(match.group(1))
            if data_type==self.DATABYTES:
                return ([0x00]*array_size,1)
            if data_type==self.DATAWORDS:
                return ([0x00]*array_size*2,1)

        # array, hex size
        array_hex = "^\[0x([0-9A-Fa-f]{1,4})\]$" # i.e. db [0xff],[0x2],[0x100],0x[23ad]
        match = re.match(array_hex,data_byte,re.IGNORECASE)
        if match:
            array_size = int(match.group(1),16)
            
            if data_type==self.DATABYTES:
                return ([0x00]*array_size,1)
            if data_type==self.DATAWORDS:
                return ([0x00]*array_size*2,1)
        
        if data_type==self.DATAWORDS:
            #If got here then treat text as a memory label
            match = re.match("^(.*)$",data_byte,re.IGNORECASE) # Should always match?
            if match:
                return (match.group(0),2)
        print("got here",data_byte,data_type)
        return (False,0)

    def make_regex(self):
        if len(self.instruction_str)==0:
            print("ERROR: No instruction set defined!")
            return False

        if self.instruction_str[-1]=="#": self.instruction_str=self.instruction_str[:-1]

        opcodes = self.instruction_str.split("#")
        for machine_code,opcode in enumerate(opcodes):
            regex = "^" + opcode
            regex = regex.replace("@@","(@@)")
            regex = regex.replace("[","\[") # escape angle brackets
            regex = regex.replace("]","\]")
            regex = regex.replace("+","\+") # escape +
            regex = regex.replace("@","[0-9A-Fa-f]") # @ is a hex character
            regex += "$"
            # hex matching on numbers and generate call/jmp regex for text?
            self.asmregex.append((regex,machine_code))

            self.lookupASM.append(opcode) # useful for debug purposes - appears never to be used!

        self.asmregex.append(("^0x([0-9A-Fa-f]{4}):$",self.ADDRESS_DEFINITION))
        self.asmregex.append(("^(.*):$",self.LABEL_DEFINITION))

        JMPs = ["JZ","JNZ","JE","JNE","JG","JGE","JL","JLE","JMP","JC","JNC"]
        CALLs =["CALL_Z","CALL_NZ","CALL_E","CALL_NE","CALL_G","CALL_GE","CALL_L","CALL_LE","CALL","CALL_C","CALL_NC"]

        callsAndjmps = JMPs+CALLs
        
        for instruction in CALLs:
            regex = "^("+instruction+" )([^0^x].*)$"
            self.asmregex.append((regex,self.MEMORY_LABEL))

        for instruction in JMPs:
            regex = "^("+instruction+" )([^0^x].*)$"
            self.asmregex.append((regex,self.MEMORY_LABEL))        

        self.asmregex.append(("^db (.*)$",self.DATABYTES))
        self.asmregex.append(("^dstr '(.*)'$",self.DATASTRING))
        self.asmregex.append(("^dw (.*)$",self.DATAWORDS))

        # use memory labels with some instructions:
        self.asmregex.append(("^(MOV r0r1,)([^0^x].*)$",self.MEMORY_LABEL)) # this could be generalised in future to all 16-bit memory reference instructions
        self.asmregex.append(("^(MOV r2r3,)([^0^x].*)$",self.MEMORY_LABEL)) # this could be generalised in future to all 16-bit memory reference instructions
        self.asmregex.append(("^(MOV r4r5,)([^0^x].*)$",self.MEMORY_LABEL)) # this could be generalised in future to all 16-bit memory reference instructions
             
        
        return True
    
    def machinecode(self,asm_line):
        matched = False
        machine_code=[]
        if asm_line=="":
            return []
        
        for regex_opcode,opcode in self.asmregex:
            match_result = re.match(regex_opcode,asm_line,re.IGNORECASE)
            if match_result:
                machine_code.append(opcode)
                for match in match_result.groups():
                    if opcode!=self.DATASTRING:
                        try:
                            machine_code.append(int("0x"+match,16))
                        except ValueError:
                            machine_code.append(match)
                    else:
                        machine_code.append(match) # Need to make sure strings (i.e. 'af' don't get turned into ints
                matched=True
        if matched==False:
            return False
        return machine_code
    
    def clean_operands(self,operands):
        # takes a list of comma separated operands and processes it so that
        # all operands are separated and cleaned of white space
        if operands=="":
            return []
        operand_list = [o.strip() for o in operands.split(",")]
        return operand_list
    
    def clean_line(self,line):
        # We could assume that assembly we're given is well formatted, but
        # safest to clean it up a little first and package it back into
        # the expected format
        
        if line=="": return ""    # Empty line

        if " " in line:
            opcode,operands = line.split(" ",1)
        else:
            opcode,operands = line,""
  
        operands = self.clean_operands(operands)
        
        if len(operands)>0:            
            cleaned = opcode+" "+",".join(operands)
        else:
            cleaned = opcode
        return cleaned

    def burn_binary(self):
        size = self.maxPOS+1
        binfilename = self.asmfilename.split('.')[0]+".bin"
        print("Burning binary..."+binfilename+" size:"+str(size)+" bytes")
        f = open(binfilename,"wb")
        f.write(self.memory[0:size])
        f.close()
        print("Binary written")

if __name__=="__main__":
    #from .define_instructions import define_instructions
    memory = bytearray(0x10000)
    #asm = Assembler("asm files\\boot.txt",memory,"")
    filename="G:\\test.asm"
        
    asm = Assembler(filename,memory,"")
    success = asm.assemble()
    if success:
        print("Assembling successful")
        for lab in asm.labels:
            print(lab,":",hex(asm.labels[lab]))
        asm.burn_binary()
    else:
        print("Assembling failed!")

