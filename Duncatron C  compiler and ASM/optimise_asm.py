import re

class Optimiser:
    def __init__(self, pattern_dict={}):
        self.pattern_dict = {"*h":"[0-9A-Fa-f][0-9A-Fa-f]","*t":".*"} # double Hex characters by default
        self.pattern_dict.update(pattern_dict)
        self.patterns=[]
        self.replacements=[]
        self.processes=[]

    def addPattern(self, pattern,replacement,process=None):
        regex_pattern = []
        for p in pattern:   # go through pattern line-by-line (list)
            regex_p = self.getRegex(p)
            regex_pattern.append(regex_p)
        
        self.patterns.append(regex_pattern)
        self.replacements.append(replacement)
        self.processes.append(process)
        
        return len(self.patterns)-1 # could be used as an index ID
    
    def getRegex(self, string):
        for p in self.pattern_dict:
            string = string.replace(p,"("+self.pattern_dict[p]+")")
        string="^"+string+"$"
        return string

    def subParameters(self, original, parameter_list):
         # replace %0, %1..%n arguments with group_list parameters
        for m in re.finditer("%[0-9]*",original):
            param_id = m.group(0)
            param_index = int(param_id[1:])
            original=original.replace(param_id,parameter_list[param_index])

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
            new_lines.append(self.subParameters(line,param_list))

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
                if updated: optimisation_finished=False
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
                    
                test = None
                if line_index < len(text_lines):
                    test = re.match(optim_line,text_lines[line_num+optim_lineN])
                if test:
                    removed_lines+=text_lines[line_num+optim_lineN]
                    for g in test.groups():
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
            

if __name__  == "__main__":
    asmOptimiser = Optimiser(pattern_dict = {"*r":"r0|r1|r2|r10","*j":"je|jne|jle|jl|jge|jg|jz|jnz"})

    asmOptimiser.addPattern(["mov *r,1","cmp A,B","*j *t","mov %0,0","%2:","mov A,%0","cmp A,0x00","jz *t"],["cmp A,B","%1 %3"])
    asmOptimiser.addPattern(["mov B,0x*h","cmp A,B"],["cmp A,0x%0"])
    asmOptimiser.addPattern(["mov A,0x*h","mov B,0x*h","add A,B"],["mov A,(0x%0+0x%1)"],process=lambda a: '0x{:02X}'.format(int(eval(a))))
    asmOptimiser.addPattern(["mov B,0x*h","mov *t,B","mov A,0x%0","mov *t,A"],["mov A,0x%0","mov %1,A","mov %2,A"])

    orig_text = "mov B,0x42\nmov [0x23],B\nmov A,0x42\nmov [0x24],A\nmov A,0x10\nmov B,0x01\nadd A,B\nblah\nmov r0,1\ncmp A,B\nje cond8\nmov r0,0\ncond8:\nmov A,r0\ncmp A,0x00\njz ifFalse7\nblah\nmov B,0x12\ncmp A,B\nblah\nbra"
    opt_text=asmOptimiser.ApplyAll(orig_text)
       
    print("***** BEFORE ******")
    print(orig_text)
    print("****** AFTER ******")
    print(opt_text)
