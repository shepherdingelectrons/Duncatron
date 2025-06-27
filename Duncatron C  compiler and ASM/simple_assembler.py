import re
import CPUSimulator.define_instructions

class Assembler:
    ADDRESS_DEFINITION = 256
    LABEL_DEFINITION = 257

    MEMORY_LABEL = 258
    
    DATABYTES = 259
    DATASTRING = 260
    DATAWORDS = 261

    UART_CHAR = 262
    EQU_SYMBOL = 263

    
    def __init__(self,filename,memory,text="",loadPOS=0):
        self.lines = []
        self.memory = memory
        self.maxPOS = 0
        self.startPOS = loadPOS
        self.instruction_str = CPUSimulator.define_instructions.instruction_str
        if filename!=None:
            self.read_and_clean_file(filename)
        else:
            self.read_and_clean_text(text)

        self.asmfilename = filename
        self.asmregex = []
        self.labels = {} # Dictionary of labels and their memory addresses
        self.labelref = []
        self.equ_symbols = {}

        self.lookupASM = []

        self.pointer = 0

        self.POPT_opcode = None
        self.RET_opcode = None
        self.INT_opcode = None
        self.RETI_opcode = None
        self.PUSHPC_opcode = None

        self.was_POPT = False
        self.was_PUSHPC = False
     
    def read_and_clean_text(self,text):
        print("Warnng, this doesn't implement safe ; and : handling, unlike read_and_clean_file")
        for line in text.split("\n"):
            if ";" in line:
                line = line[:line.find(";")]
            self.lines.append(line.strip())
    
    def read_and_clean_file(self,filename):
        with open(filename,encoding="utf-8") as file:
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

    def add_equ_symbol(self, symbol, replacement_value):
        if symbol in self.equ_symbols:
            return False
        self.equ_symbols[symbol] = replacement_value
        self.equ_symbols['['+symbol+']'] = '['+replacement_value+']' # also add as addressing
        return True
    
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
    
    def assemble(self, show_labels=False):
        print("Making regex...")
        if not self.make_regex(): return False
        print("Regex complete")
        self.POPT_opcode = self.machinecode("POP T")[0]
        self.RET_opcode = self.machinecode("RET")[0]
        self.INT_opcode = self.machinecode("INT")[0]
        self.RETI_opcode = self.machinecode("RETI")[0]
        self.PUSHPC_opcode = self.machinecode("PUSH_PC+1")[0]
        
        self.pointer = self.startPOS
        for line_number,line in enumerate(self.lines):
            cleaned_line = self.clean_line(line)
            if cleaned_line==False:
                print("Error processing line #"+str(line_number)+": "+line)
                return False

            success_state = self.process_asm_line(cleaned_line,line_number)
            if type(success_state) == str: # a new string was returned, try (once) to decode again
                success_state = self.process_asm_line(success_state,line_number)

            if success_state!=True:
                return False

        success = self.backfill_references()
        
        if success and show_labels:
            for lab in self.labels:
                print(lab,":",hex(self.labels[lab]),self.labels[lab])

        if success:
            self.trim_binary()
            
        return success

    def process_asm_line(self,cleaned_line,line_number):
        asm = self.machinecode(cleaned_line)
        
        if asm:
            opcode = asm[0]

            # try to flag some likely sources of programming bugs
            
            if opcode==self.RET_opcode and self.was_POPT==False:
                print("RET must be preceeded by 'POP T', line number:",line_number)
                return False
            if opcode==self.INT_opcode and self.was_PUSHPC==False:
                print("INT must be preceeded by 'PUSH_PC+1', line number:", line_number)
##                if opcode in CALL_opcodes and was_PUSHPC==False:
            if len(cleaned_line)>=4: ## Detect CALLs this way
                if cleaned_line[:4].upper()=="CALL" and self.was_PUSHPC==False and ":" not in cleaned_line:
                    print("CALLs must be preceeded by 'PUSH_PC+1', line number:", line_number)
                    return False
            if opcode==self.RETI_opcode and self.was_POPT:
                print("RETI should NOT be preceeded by 'POP T', line number:", line_number)
            
            self.was_POPT = (opcode==self.POPT_opcode)
            self.was_PUSHPC = (opcode==self.PUSHPC_opcode)
            
            if opcode<256: # a normal instruction, write into memory
                print(cleaned_line)
                for byte in asm:
                    self.write_memory(self.pointer,byte)#self.memory[pointer]=byte
                    self.pointer+=1
            elif opcode==self.ADDRESS_DEFINITION: # other behaviour specified
                if asm[1]<self.pointer:
                    print("ERROR. Memory label ("+hex(asm[1])+") on line number",line_number,"must be declared at higher address than current pointer ("+hex(self.pointer)+")")
                    return False
                self.pointer=asm[1]
            elif opcode==self.LABEL_DEFINITION:
                if not self.add_label(asm[1],self.pointer):
                    return False

            elif opcode == self.MEMORY_LABEL:
                self.pointer = self.add_call_or_jmp_reference(asm[1],asm[2],self.pointer,1,pureData=False)
            elif opcode == self.DATABYTES or opcode == self.DATAWORDS:
                #print(asm[1],type(asm[1]))
                asm[1]=str(asm[1])
                
                if "," in asm[1]:
                    bytelist = asm[1].split(",")
                else:
                    bytelist = [str(asm[1])]
               
                for databyte in bytelist:
                    #print(databyte,":",bytelist,cleaned_line,line_number)
                    int_bytelist,status = self.process_databyte(databyte.strip(),opcode)
                    if status==0:
                        print("Could not process data byte/word '"+databyte+"' at line number:",line_number,"Line:",cleaned_line)
                        return False
                    elif status==1:
                        print(cleaned_line)
                        for byte in int_bytelist:
                            self.write_memory(self.pointer,byte)
                            #print("Writing:",pointer,byte)
                            self.pointer+=1
                    elif status==2:
                        # treat as a memory label
                        self.pointer = self.add_call_or_jmp_reference("",int_bytelist,self.pointer,0,pureData=True)
            elif opcode == self.DATASTRING:
                datastr = self.process_datastring(asm[1])
                for character in datastr:
                    self.write_memory(self.pointer,ord(character))#self.memory[pointer]=ord(character)
                    self.pointer+=1
                self.write_memory(self.pointer,0)#self.memory[pointer]=0 # Add zero terminator automatically
                self.pointer+=1
            elif opcode == self.UART_CHAR:
                uart_byte = ord(asm[1])
                UART_OPCODE = self.machinecode("MOV U,0x00")[0]
                self.write_memory(self.pointer,UART_OPCODE)
                self.write_memory(self.pointer+1,uart_byte)
                self.pointer+=2
            elif opcode == self.EQU_SYMBOL:
                if self.add_equ_symbol(asm[1],asm[2])==False:
                    print("Symbol",asm[1],"already defined on line:",line_number)
                    return False
            else:
                print("Don't know how to process opcode! OPCODE=",opcode)
                return False
        elif asm==False:
            
            # command formats:
            # int
            # jmp 0x@@@@
            # cmp A,0x04
            symbol_found=False
            
            if " " in cleaned_line:
                print(cleaned_line)
                opcode,p0 = cleaned_line.split(" ")
                p1 = None
                if "," in p0:
                    p0,p1 = p0.split(",")
                print(opcode,p0,p1)
                if p0 in self.equ_symbols:
                    p0 = self.equ_symbols[p0]
                    symbol_found=True
                if p1 in self.equ_symbols:
                    p1 = self.equ_symbols[p1]
                    symbol_found=True
                                
                
                new_line = opcode+" "+p0
                if p1!=None:
                    new_line+=","+p1
                
            if symbol_found:
                #print("Symbol replaced:",new_line)
                return new_line
            else:
                print("Failed to generate machine code on line:",line_number,":",cleaned_line)
            return False
        return True
    
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

        if data_byte=='':
            print("ERROR: Data byte is NULL")
            return (False,0)
        
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

        # Use characters for mov U,0x@@, i.e. mov U,'A'
        self.asmregex.append(("^MOV U,'(.)'$",self.UART_CHAR))

        # EQU symbol support
        self.asmregex.append(("^(.*) equ (.*)$",self.EQU_SYMBOL))
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
                    if opcode!=self.DATASTRING and opcode!=self.UART_CHAR:
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

    def trim_binary(self):
        # removes trailing zeros from file to allow defining variables in RAM easily
        last_data_pos = 0
        first_data_pos = 0x10000
        for pos,byte in enumerate(self.memory):
            if byte!=0:
                if first_data_pos>pos:
                    first_data_pos=pos
                last_data_pos = pos
        print("Trimmed binary: first data pos =",first_data_pos,"last data pos = ", last_data_pos)

        self.startPOS = first_data_pos
        self.maxPOS = last_data_pos+1 # Add one in case the last byte is a zero-terminated string

    def burn_binary(self):
        size = self.maxPOS+1
        binfilename = self.asmfilename.split('.')[0]+".bin"
        print("Burning binary..."+binfilename+" size:"+str(size)+" bytes")
        f = open(binfilename,"wb")
        f.write(self.memory[self.startPOS:size])
        f.close()
        print("Binary written")

    def burn_headerfile(self):
        size = self.maxPOS+1-self.startPOS
        Hfilename = "BurnProgram.h" #self.asmfilename.split('.')[0]+".h"
        print("Burning header file..."+Hfilename+" size:"+str(size)+" bytes")

        import datetime
        import os
        import time

        print("Time is:",time.ctime())
        time_seconds = int(time.time())  # seconds elapsed since 1st Jan 1970 

        script_name = os.path.basename(__file__)

        f = open(Hfilename,"w")

        f.write("// File generated automatically by "+script_name+"\n")
        f.write("// Source ASM: "+str(self.asmfilename)+"\n")
        now = datetime.datetime.now()
        f.write("// File created: "+str(now)+"\n\n")
        f.write("#define BURN_BINARY 1\n\n")
        unique_ID = "0x{:08x}".format(time_seconds)
        f.write("uint32_t unique_ID = "+unique_ID+"; // Stored in EEPROM when burnt to avoid re-burning\n")
        f.write("uint16_t program_code_len = "+str(size)+"; // Size in bytes\n")
        f.write("uint16_t program_start = "+hex(self.startPOS)+"; // Starting address in memory\n\n")

        f.write("const PROGMEM uint8_t BurnProgram[] = {")
        for b_num,b in enumerate(self.memory[0:size]):
            if b_num % 16 == 0:
                f.write("\n")
            f.write("0x{:02x}".format(b))
            if b_num!=size-1:
                f.write(",")
            
        f.write("};\n")
        f.close()
        print("Header file written")

if __name__=="__main__":
    #from .define_instructions import define_instructions
    memory = bytearray(0x10000)
    #asm = Assembler("asm files\\boot.txt",memory,"")
    filename="..\Building\\SystemOS.asm"
    #filename = "SystemOS.asm"
    #filename = "asm files\\super_simple_halt.asm"
    asm = Assembler(filename,memory,"")
    success = asm.assemble()
    if success:
        print("Assembling successful")
        for lab in asm.labels:
            print(lab,":",hex(asm.labels[lab]))
        asm.burn_binary()
        asm.burn_headerfile()
        print(asm.equ_symbols)
    else:
        print("Assembling failed!")

