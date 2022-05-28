import re

class Optimiser:
    def __init__(self, temp_regs):
        temp_reg_match = self.build_temp_reg_match(temp_regs) 
        pattern_dict = {"*r":"r0|r1|r2|r3|r4|r5","*j":"je|jne|jle|jl|jge|jg|jz|jnz","*m":temp_reg_match,"*J":"jmp|je|jne|jle|jl|jge|jg|jz|jnz"}
        self.pattern_dict = {"*h":"[0-9A-Fa-f][0-9A-Fa-f]","*t":".*"} # double Hex characters by default
        self.pattern_dict.update(pattern_dict)
        self.patterns=[]
        self.replacements=[]
        self.processes=[]
        self.shoutouts=[]

    def addPattern(self, pattern,replacement,process=None,shoutout=False):
        regex_pattern = []
        for p in pattern:   # go through pattern line-by-line (list)
            regex_p = self.getRegex(p)
            regex_pattern.append(regex_p)
        
        self.patterns.append(regex_pattern)
        self.replacements.append(replacement)
        self.processes.append(process)
        self.shoutouts.append(shoutout)
        
        return len(self.patterns)-1 # could be used as an index ID
    
    def build_temp_reg_match(self,temp_regs):
        temp_reg_match=""
        for tr in temp_regs:
            for c in tr:
                addc=c
                if c=="[" or c=="]": addc="\\"+c # Add escape characters for memory locations
                temp_reg_match+=addc
            temp_reg_match+="|"
        if temp_reg_match: temp_reg_match=temp_reg_match[:-1]
        return temp_reg_match
    
    def getRegex(self, string):
        for p in self.pattern_dict:
            string = string.replace(p,"("+self.pattern_dict[p]+")")
        string="^"+string+"$"
        return string

    def subParameters(self, original, parameter_list,removeEscapes=False):
         # replace %0, %1..%n arguments with group_list parameters
        for m in re.finditer("%[0-9]*",original):
            param_id = m.group(0)
            param_index = int(param_id[1:])
            replace_text = parameter_list[param_index]
            if removeEscapes: replace_text = replace_text.replace('\\','') # remove escape characters
            original=original.replace(param_id,replace_text)

        # escape [ ] characters
        processed = ""
        for char in original:
            new_char=char
            #if char=="[" or char=="]": new_char="\\"+char # Is this line needed?
            processed+=new_char
        return processed

    def getReplacement(self, pattern_id, param_list):
        new_lines=[]
        for line in self.replacements[pattern_id]:
            new_lines.append(self.subParameters(line,param_list,removeEscapes=True))

        return new_lines
    
    def processLine(self, line, pattern_id):
        function = self.processes[pattern_id]
        if function:
            parens_match = re.match(".*\((.*)\)",line)
            if parens_match:
                for p in parens_match.groups():
                    new_p = function(p)
                    line = line.replace("("+p+")",new_p)
        return line
        
    def ApplyAll(self, text):
        optimisation_finished=False
        while optimisation_finished==False:
            print("Optimising...")
            optimisation_finished=True

            for optim_num, optim in enumerate(self.patterns):
                text,updated = self.ApplyOptimisation(text,optim_num)
                if updated:
                    optimisation_finished=False
                    if self.shoutouts[optim_num]:
                        print("Optimisation #"+str(optim_num)+" applied!")
        return text
    
    def ApplyOptimisation(self, text, pattern_id):
        text_lines = text.split('\n')
        
        opt_text = ""
        line_num=0
        optim = self.patterns[pattern_id]

        removed_lines=""
        update = False
        
        while line_num<len(text_lines):
            curr_line = text_lines[line_num]
            curr_line = curr_line.strip("\t") # remove tabs
            if ";" in curr_line:
                colon = curr_line.find(";")
                curr_line = curr_line[:colon]

            nomatch=False
            line_len = 0
            group_list=[]
                      
            for optim_lineN, optim_line in enumerate(optim):
                line_index = line_num+optim_lineN
                if "%" in optim_line:
                    optim_line = self.subParameters(optim_line,group_list)
                    if self.shoutouts[pattern_id]: print(group_list)
                test = None
                if line_index < len(text_lines):
                    test = re.match(optim_line,text_lines[line_num+optim_lineN])
                if test:
                    removed_lines+=text_lines[line_num+optim_lineN]
                    for g in test.groups():
                        if "[" in g: g=g.replace("[","\[")
                        if "]" in g: g=g.replace("]","\]")
                        group_list.append(g)
                    line_len+=1
                else:
                    nomatch = True
                    break

            if nomatch:
                #if curr_line!="\n":
                #print(curr_line,len(curr_line))
                if len(curr_line)>0:
                    opt_text+=curr_line+"\n"
                removed_lines=""
                line_num+=1 # test next line for matches
            else:
                # matched an entire set so skip past lines changed
                replace_text = self.getReplacement(pattern_id,group_list)
                #print("Matched lines:",removed_lines)
                processed_text = ""
                for rline in replace_text:
                    rline = self.processLine(rline,pattern_id)
                    opt_text+=rline+"\n"
                    processed_text+=rline
                #print("Replaced with:",processed_text)
                update = True
                
                line_num+=line_len
                removed_lines=""
                
        return (opt_text,update)

    def optimise_code(self, ASMcode):
        # Conditional jumping optimisations
        inverse_conditionals = {"jl":"jge","jg":"jle","je":"jne","jne":"je","jle":"jg","jge":"jl","jz":"jnz","jnz":"jz"}
        self.addPattern(["mov *m,0x01","cmp A,B","*j *t","mov %0,0x00","%2:","mov A,%0","cmp A,0x00","jz *t"],["cmp A,B","(%1) %3"],process=lambda a:inverse_conditionals[a]) # temp register storage
        self.addPattern(["mov *m,0x01","cmp A,B","*j *t","mov %0,0x00","%2:","mov A,%0","cmp A,0x00","jnz *t"],["cmp A,B","%1 %3"]) # temp register

        # dowhile optimisations:
        self.addPattern(["mov A,*t","mov B,*t","push A","mov A,B","inc A","mov %1,A","mov B,A","pop A"],["mov A,%1","inc A","mov %1,A","mov B,A","mov A,%0"],shoutout=True)
        self.addPattern(["mov A,*t","mov B,*t","push A","mov A,B","dec A","mov %1,A","mov B,A","pop A"],["mov A,%1","dec A","mov %1,A","mov B,A","mov A,%0"],shoutout=True)
        
        self.addPattern(["mov *m,*t","push A","mov A,%0","inc A","mov %1,A","mov %0,A","pop A"],["mov A,%1","inc A","mov %1,A","mov %0,A"])
        self.addPattern(["mov *m,*t","push A","mov A,%0","dec A","mov %1,A","mov %0,A","pop A"],["mov A,%1","dec A","mov %1,A","mov %0,A"])
        # Remove unnecessary intermediate registers (without swapping A and B):
        self.addPattern(["mov *m,A","mov A,*t","mov B,%0"],["mov B,A","mov A,%1"])
        
        # Optimise for A = 0xXX + 0xYY
        self.addPattern(["mov A,0x*h","mov B,0x*h","add A,B"],["mov A,(0x%0+0x%1)"],process=lambda a: '0x{:02X}'.format(int(eval(a))&0xff))
        # Optimise for A = 0xXX - 0xYY
        self.addPattern(["mov A,0x*h","mov B,0x*h","sub A,B"],["mov A,(0x%0-0x%1)"],process=lambda a: '0x{:02X}'.format(int(eval(a))&0xff))
       
        # Optimise for: r0 = A, A = r0 + B = A + B
        self.addPattern(["mov *r,A","mov A,*t","mov B,%0","add A,B"],["mov B,%1","add A,B"]) # Kinda assumes that register %0 is not used later on.
        self.addPattern(["mov *m,A","mov A,*t","mov B,%0","add A,B"],["mov B,%1","add A,B"]) # Kinda assumes that register %0 is not used later on.

        # Optimise for cmp A directly to literal
        self.addPattern(["mov B,0x*h","cmp A,B"],["cmp A,0x%0"])

        # Optimise for inc A
        self.addPattern(["mov B,0x01","add A,B"],["inc A"])

        # Optimise for dec A
        self.addPattern(["mov B,0x01","sub A,B"],["dec A"])

##        # Optimise for xor A
##        self.addPattern(["mov A,0x00"],["xor A"])

        # Remove repeated labels
        self.addPattern(["*t:","*t:"],["(%0,%1):"],process=lambda a: curate_labels(a))

        # Remove repetition when moving a value into multiple memory locations/registers
        self.addPattern(["mov B,0x*h","mov *t,B","mov A,0x%0","mov *t,A"],["mov A,0x%0","mov %1,A","mov %2,A"])

        # For loop optimisation
        self.addPattern(["mov \[0x*t],A","*t:","mov A,\[0x%0]"],["mov [0x%0],A","%1:"]) 

        opt_text = self.ApplyAll(ASMcode)

        # make list of out of date labels from label_remap and use that to do a search pattern (include jmp)
        remap_jmps = self.addPattern(["*J *t"],["%0 (%1)"],process=lambda a:GetRemapLabel(a)) 

        opt_text,updated = self.ApplyOptimisation(opt_text,remap_jmps)
        #print(opt_text)
        return(opt_text)

        # notes on possible optimisations:

        # DONE - (1)- if/while conditional logic when only a single level deep - can be substantially optimised4
        # (2) mov B,0xXY
        # cmp A,B -->> cmp A,0xXY
        # DONE - remove multiple labels and track so jumps can be updated

        # Per function (OptimiseFunctionsForRegisters):
        #   - What registers are not used in this function?
        #   - What variables (memory) are used most often?
        #   - Sort memory usage and map memory-variables to unused registers
        #   - Note that function modifies registers so should push/pop them (within the function) onto/from the stack.

        # asm... use #pragma statements

label_remap={}
def curate_labels(labels):
    label0,label1=labels.split(',')
   # label0 is going to replace label1
       
    label_remap[label1]=label0
    return label0

def GetRemapLabel(l):
    while l in label_remap:
        l = label_remap[l]
    return l


if __name__  == "__main__":
    temp_regs = ["r0","r1","r2","r3","r4","r5"]
    asmOptimiser = Optimiser(temp_regs)

    asmOptimiser.addPattern(["mov *r,0x01","cmp A,B","*j *t","mov %0,0x00","%2:","mov A,%0","cmp A,0x00","jnz *t"],["cmp A,B","%1 %3"])
##    asmOptimiser.addPattern(["mov B,0x*h","cmp A,B"],["cmp A,0x%0"])
##    asmOptimiser.addPattern(["mov A,0x*h","mov B,0x*h","add A,B"],["mov A,(0x%0+0x%1)"],process=lambda a: '0x{:02X}'.format(int(eval(a))))
##    asmOptimiser.addPattern(["mov B,0x*h","mov *t,B","mov A,0x%0","mov *t,A"],["mov A,0x%0","mov %1,A","mov %2,A"])

    orig_text = "mov [0x01],B\nenterdowhile10:\nmov U,0x41\nmov A,[0x01]\ninc A\nmov [0x01],A\nmov B,0x19\nmov r3,0x01\ncmp A,B\njl cond10\nmov r3,0x00\ncond10:\nmov A,r3\ncmp A,0x00\njnz enterdowhile10\nmov A,[0x01]\nmov B,0x41\nadd A,B"

##    "mov B,0x42\nmov [0x23],B\nmov A,0x42\nmov [0x24],A\nmov A,0x10\nmov B,0x01\nadd A,B\nblah\nmov r0,1\ncmp A,B\nje cond8\nmov r0,0\ncond8:\nmov A,r0\ncmp A,0x00\njz ifFalse7\nblah\nmov B,0x12\ncmp A,B\nblah\nbra"
    opt_text=asmOptimiser.ApplyAll(orig_text)
       
    print("***** BEFORE ******")
    print(orig_text)
    print("****** AFTER ******")
    print(opt_text)

    
