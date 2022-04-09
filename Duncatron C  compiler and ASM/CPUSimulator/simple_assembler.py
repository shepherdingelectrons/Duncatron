import define_instructions
import re

class Assembler:
    def __init__(self,filename,memory):
        self.lines = []
        self.memory = memory
        self.instruction_str = ""
        self.read_and_clean_file(filename)
        self.asmregex = []
    
    def read_and_clean_file(self,filename):
        with open(filename) as file:
            for line in file:
                if ";" in line:
                    line = line[:line.find(";")]
                self.lines.append(line.strip())

    def assemble(self):
        if not self.make_regex(): return False
        
        pointer = 0
        for line_number,line in enumerate(self.lines):
            cleaned_line = self.clean_line(line)
            if cleaned_line==False:
                print("Error processing line #"+str(line_number)+": "+line)
                return False

            asm = self.machinecode(cleaned_line)
            if asm:
                for byte in asm:
                    self.memory[pointer]=byte
                    pointer+=1
                
        return True

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
                    machine_code.append(int("0x"+match,16))             
                matched=True
        if matched==False:
            print("Could not match line:",asm_line)
            return []
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
        if ":" in line:
            operand,non_label = line.split(":",1)
            non_label=non_label.strip()
            if non_label.strip()!="":
                print("Unexpected characters '"+non_label+"' after ':'")
                return False
            if " " in operand:
                print("Unexpected " " in label:",operand)
                return False

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
        
if __name__=="__main__":
    memory = bytearray(0x10000)
    asm = Assembler("testasm3.txt",memory)
    asm.instruction_str = define_instructions.instruction_str

    #asm.asmregex.append(("call .*",0xFE
    success = asm.assemble()
    if success:
        print("Assembling successful")
    else:
        print("Assembling failed!")
    
##asm("MOV B,0x20")
##asm("ADD A,B")
##asm("JMP 0x1234")
##
##print(asm("CALL 0x1200"))
##print(asm("CALL 0x1234"))

