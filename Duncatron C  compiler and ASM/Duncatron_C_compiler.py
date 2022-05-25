# Dependencies:
# pycparser
# install with:
# pip install pycparser

from __future__ import print_function
import sys
import re

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
#
#sys.path.extend(['.', '..'])
from pycparser import c_parser

#variables = {} # type, init, address
RAM_START = 0x8800
RAM_END = 0xFFFF
ZERO_PAGE = 0x8800

RAM = bytearray(1+RAM_END-RAM_START)

nodeASM = {"TypeDecl":"mov A,%0\nmov [%1],A\t;%2=%0\n",
           "FuncDecl":"%0:\n",
           "AssignVarFromA":"mov [%0],A\t;'%1'=A\n",
           "AssignAFromLit":"mov A,%0\n",
           "AssignAFromMem":"mov A,[%0]\n"}

reg_list={"r0":0,"r1":0,"r2":0,"r3":0,"r4":0,"r5":0}
conditionals = {"<":"jl",">":"jg","==":"je","!=":"jne","<=":"jle",">=":"jge","!":"jz"}
temp_regs=[] # List of all regs and memory locations used as temporary registers

class Variables:
    def __init__(self):
        self.varlists = {}

    def print(self,scope):
        print(self.varlists[scope].vars)
        
    def add_scope(self,scope):
        self.varlists[scope] = VariableList()

    def add(self,scope,var_name,var_type,var_value,address):
        self.varlists[scope].new(var_name,var_type,var_value,address)
        
    def get_type(self,scope,var_name):
        if not var_name in self.varlists[scope].vars:
            scope="" # Global scope
        return self.varlists[scope].get_type(var_name)

    def get_value(self,scope,var_name):
        if not var_name in self.varlists[scope].vars:
            scope="" # Global scope
        return self.varlists[scope].get_value(var_name)

    def get_address(self,scope, var_name):
        if not var_name in self.varlists[scope].vars:
            scope="" # Global scope
        return self.varlists[scope].get_address(var_name)

    def contains(self,scope,var_name):
        # Check global and local scope
        if not var_name in self.varlists[scope].vars:
            scope=""
        return var_name in self.varlists[scope].vars

    def reference(self,scope,var_name):
        if self.contains(scope,var_name):
            address = self.get_address(scope,var_name)
            var_name = "["+formatNumber(address)+"]"
        return var_name
        
class VariableList:
    VARTYPE = 0
    VARVALUE = 1
    VARADDR = 2
    def __init__(self):
        self.vars = {}

    def new(self, var_name,var_type,var_value,address):
        self.vars[var_name]=[var_type,var_value,address]

    def get_type(self, var_name):
        return self.vars[var_name][self.VARTYPE]

    def get_value(self, var_name):
        return self.vars[var_name][self.VARVALUE]
                 
    def get_address(self, var_name):
        return self.vars[var_name][self.VARADDR]
    
def getReg(reg=None):
    for r in reg_list:
        if reg_list[r]==0: 
            reg_list[r]=1
            #print("Register:",r,"got")
            if r not in temp_regs: temp_regs.append(r)
            return r

    # We should return a free memory address in RAM, starting from zero page
    addr = "["+formatNumber(NextMemorySlot(start=ZERO_PAGE))+"]"
    #print("Register:",addr,"got")
    if addr not in temp_regs: temp_regs.append(addr)
    return addr
    
def freeReg(reg,size=1): # ADD CODE TO ALSO FREE MEMORY LOCATIONS...
    if reg in reg_list:
        reg_list[reg]=0
    elif reg!="A" and reg!="B":
        addr_str = reg[1:-1]        
        #print(reg,addr_str)
        addr = int(addr_str,base=16)
    
        if len(addr_str)==4: # Zero-page addressing
            addr += ZERO_PAGE # absolute address
            addr -= RAM_START # RAM_START is 0th element of RAM bytearray
        elif len(addr_str)==6: # 16-bit address
            addr -= RAM_START
        else:
            print("ERROR: freeReg memory address not understood")
            return
    
        for i in range(0,size):
            if RAM[addr+i]==1: # only free memory if it is a temp_memory register and not a 'permanent' variable allocation (==2)
                RAM[addr+i]=0
     
def growComment(reg_str,add):
    reg_str="("+reg_str+add+")"
    return reg_str

def formatNumber(address,force8bit=True):
    if type(address)==type(""):
        address = int(address)
    
    if address&0xFF00==ZERO_PAGE or force8bit:
        AddrStr='0x{:02X}'.format(address&0xFF)
    else:
        AddrStr='0x{:04X}'.format(address&0xFF)
    return AddrStr
        
def FreeMemory(address):
    #print("Freeing memory address:",address,hex(address))
    RAM[address-RAM_start]=0
    
def NextMemorySlot(start=RAM_START,size=1,perm=0): # absolute addressing
    FreeSlot=None
    slotsize=0
    for address,m in enumerate(RAM):
        if address+RAM_START>=start:
            if m==0: # if we have found a valid empty memory byte
                if FreeSlot==None:
                    FreeSlot=address+RAM_START
                slotsize+=1
                if slotsize==size:
                    for i in range(0,size):
                        RAM[FreeSlot-RAM_START+i]=1+perm
                    break
            else:
                FreeSlot=None
            
    return FreeSlot

class Compiler:
    def __init__(self):
        self.local_scope = "" #global
        self.variables=Variables()
        self.variables.add_scope("") # This is global scope
        self.ASMcode=""
        self.FuncASTlist=[]
        self.inherit_dict = {}
        self.verbose = False

    def resetSystem(self):
        # Called so we can compile with another object and not get mixed up with previous compilation
        # Clear RAM, reset reg_list and clear temp_regs
        for a in range(len(RAM)):
            RAM[a] = 0

        for r in reg_list:
            reg_list[r]=0

        temp_regs = []

        global label_number, all_labels

        label_number=0
        all_labels = []
        
        self.__init__()

    def compile(self,ctext,verbose=False):  #
        self.resetSystem()
        
        print("Starting compile...")
        parser = c_parser.CParser()
        ast = parser.parse(ctext, filename='<none>')
        
        self.ASMcode=""
        self.FuncASTlist=[] # List of all non-main functions as AST nodes
        
        self.local_scope=""
        self.verbose=verbose
        # walkAST on global declarations and main function.  Stores other functions in FuncASTlist    
        self.walkAST(ast)
    
        for func in self.FuncASTlist:
            self.walkAST(func)
            self.addASM("ret")

        return self.ASMcode
    
    def addASM(self, nt,arg0=None,arg1=None,arg2=None):
        if nt in nodeASM:
            line=nodeASM[nt]
            line=line.replace("%0",str(arg0))
            line=line.replace("%1",str(arg1))
            line=line.replace("%2",str(arg2))
            self.ASMcode+=line
        else:
            self.ASMcode+=nt+"\n"
            #print("Warning: no ASM for node type:",nt)
    
    def inherit(self, key,item):
        self.inherit_dict[key]=item

    def deinherit(self,key):
        self.inherit_dict.pop(key)
        
    def walkAST(self,statement,loadReg=None,silent=False):
        if statement is None: return None
        node_type=statement.__class__.__name__
        if self.verbose: print("node_type=",node_type)
        
        if node_type=="Decl":
            #print(statement)
            var_name = statement.name
            var_type,type_class = self.walkAST(statement.type)
            self.inherit("Decl",var_type)
            var_init = self.walkAST(statement.init) #return any value in the A register
            self.deinherit("Decl")
            
            if type_class=="TypeDecl":
                address = NextMemorySlot(perm=1)
                if var_init==None:
                    var_value=None
                else:
                    var_value=var_init[1]
                    if var_value!=None:
                        self.addASM("AssignAFromLit",formatNumber(var_value))
                    self.addASM("AssignVarFromA",formatNumber(address,force8bit=False),var_name)
                    freeReg("A")
                #print("Declaring:",var_name,var_type,var_value,address)
                #variables[var_name]=[var_type,var_value,address] # every variable has global scope for now..
                self.variables.add(self.local_scope,var_name,var_type,var_value,address)
            elif type_class=="FuncDecl":
                args=var_type[0]
                function_label = new_label(var_name,no_number=True)                
                self.addASM(type_class,function_label)
                
        elif node_type=="TypeDecl":
            var_type = self.walkAST(statement.type)
            return (var_type,"TypeDecl")
        
        elif node_type=="IdentifierType":
            return statement.names[0]
        
        elif node_type=="Constant":
            regvalue = formatNumber(statement.value)
            if loadReg!=None:
                if not silent:
                    self.ASMcode+="mov "+loadReg+","+formatNumber(statement.value)+"\n"
            return (statement.type,statement.value,"Constant",None,regvalue)

        elif node_type=="Assignment":
            op = statement.op
            lvalue = self.walkAST(statement.lvalue)
            rvalue = self.walkAST(statement.rvalue,"B")
            freeReg("B")
            
            # lvalue = var_type, var_value, var_name

            assign_name=lvalue[3] # Get name from ID return
            var_type=self.variables.get_type(self.local_scope, assign_name)#variables[assign_name][0] # get type
            address=self.variables.get_address(self.local_scope,assign_name)#variables[assign_name][2] # get variable memory address

            if lvalue[2]==None:
                print("ERROR: Assignment needs a name ID")

            if op=="+=" or op=="-=":
                alu_ins = "add A,B" if op=="+=" else "sub A,B"
                
                if rvalue[2]=="Constant": # B holds the constant
                    self.addASM("mov A,["+formatNumber(address)+"]") # A=variable
                    self.addASM(alu_ins) #
                    self.addASM("mov ["+formatNumber(address)+"],A")
                if rvalue[2]=="BinaryOp": # result is in A register
                    if op=="+=":
                        self.addASM("mov B,["+formatNumber(address)+"]") # B=variable
                        self.addASM("add A,B") # 
                        self.addASM("mov ["+formatNumber(address)+"],A")
                    elif op=="-=":
                        self.addASM("mov B,A") # a contains result from binaryOp - need to minus it off the leftVariable
                        self.addASM("mov A,["+formatNumber(address)+"]") # A=variable
                        self.addASM("sub A,B")
                        self.addASM("mov ["+formatNumber(address)+"],A")
                        
                if rvalue[2]=="ID": # ID contents is in B
                    self.addASM("mov A,["+formatNumber(address)+"]") #
                    self.addASM(alu_ins) # A=A+B or A=A-B
                    self.addASM("mov ["+formatNumber(address)+"],A")
                    
            if op=="=":  
                if rvalue[2]=="Constant": # Then we have a literal value that has been evaluated (and is currently in A), assign to lvalue Name
                    self.addASM("mov ["+formatNumber(address)+"],B\t;'"+assign_name+"'=B")
                elif rvalue[2]=="BinaryOp": # result is in A register
                    self.addASM("mov ["+formatNumber(address)+"],A\t;'"+assign_name+"'=A")
                elif rvalue[2]=="ID":
                    Lid_name = lvalue[3]
                    Laddr = self.variables.get_address(self.local_scope,Lid_name)#lvariables[Lid_name][2]
                    Rid_name = rvalue[3]
                    Raddr = self.variables.get_address(self.local_scope,Rid_name)#variables[Rid_name][2]

                    self.addASM("mov ["+formatNumber(Laddr)+"],A\t;'"+Lid_name+"'='"+Rid_name+"'")
                    rvalue[2]=="BinaryOp" # If the type is changed here, it means another assignment would use the BinaryOp method above and move directly from A register
                else:
                    print("ERROR PROBABLY",rvalue[2])

                

            if var_type!="int":
                print("ERROR! Unsupported type in assignment",var_type)
                   # returns a value (type,value,Constant/BinaryOp (for chain assigning)
            return (rvalue[0],rvalue[1],rvalue[2],None) # BinaryOp means
            
        elif node_type=="BinaryOp":
            op = statement.op
            
            leftNode = statement.left.__class__.__name__
            rightNode = statement.right.__class__.__name__

            leftReg = "A" # for ID or BinaryOp left-nodes

            returnRegContents=False
            rightReg = "B"

            if (leftNode=="Constant" or leftNode=="ID") and rightNode=="BinaryOp": #  Then we'll need A and B for BinaryOp
                leftReg=None
                returnRegContents=True
            if leftNode=="UnaryOp" and rightNode=="BinaryOp":
                # Means we need to put result in free register
                leftReg=getReg()
            if leftNode=="UnaryOp" and rightNode=="UnaryOp":
                leftReg=getReg()
                rightReg="A"               
                
            if leftNode=="BinaryOp" and rightNode=="BinaryOp": # There is another condition..?
                leftReg=getReg() # Get anything but A or B reg

##            if silent: # Implemented to optimise For loops
##                leftReg=None
             # type, value, node_type,var_name/None
            left = self.walkAST(statement.left,leftReg,silent=returnRegContents)
            right = self.walkAST(statement.right,rightReg)
            
            if returnRegContents: leftReg = left[4] # return regvalue

            if leftReg!="A":
                #self.ASMcode+="mov B,"+leftReg+"\n"
                invert_cond = {"<":">","<=":">=",">":"<",">=":"<="}
                if op in invert_cond: # we are being asked to evaluate a conditional statement as a binary operation (i.e. if (a<10) or while (a<10)
                    op = invert_cond[op] # the way the logic works here is opposite to

                self.addASM("mov B,"+leftReg)
                freeReg(leftReg) # oops we don't know the difference between a temp memory_reg and a variable. It's okay, freeReg will ignore if a variable
            freeReg(rightReg)

            # When leftNode is a constant or an ID:
            # There is an optimisation to be had where we don't load (say) r1 with a value,
            # only to load it later into B. Instead we could load B directly with that value.
            
            # Left and right should now contain two ints of either values or variables
            if left[0]!="int" or right[0]!="int":
                print("I don't know how to do binary operations on non-ints!")
                return None

            if op=="+":
                self.addASM("add A,B")
            elif op=="-":
                self.addASM("sub A,B")
            elif op=="&&" or op=="&":
                self.addASM("and A,B")
            elif op=="||" or op=="|":
                self.addASM("or A,B")
            elif op in conditionals:
                if loadReg=="A" or loadReg=="B" or loadReg==None:
                    status_reg = getReg() # we will use a new register
                else:
                    status_reg = loadReg # we can put result straight in report register
                    
                cond_label = new_label("cond")
                
                self.addASM("mov "+status_reg+",0x01")
                self.addASM("cmp A,B") # The order of A and B matters for some conditionals (but not all).
                # i.e.
                # mov A,0x0A
                # mov B,[0x00]
                # cmp A,B
                # jl/jle/jg/jge label0 ; jump behaviour is inverted if A and B are swapped
                #
                # alternatively:
                # je/jne/jz/jnz label0 ; jump behaviour is the same if A and B are swapped
                
                condcode = conditionals[op] # if we have swapped A and B, then need to record that and use inverse conditional here
                self.addASM(condcode+" "+cond_label)
                
                self.addASM("mov "+status_reg+",0x00")
                self.addASM(cond_label+":")

                if loadReg!=status_reg:
                   self.addASM("mov A,"+status_reg)
                   freeReg(status_reg)
                loadReg = None
            else:
                print("OPERATION '"+op+"' not supported!")

            if loadReg is not None and loadReg!="A" and loadReg!="B":
                self.addASM("mov "+loadReg+",A")
                #print("loadreg=",loadReg,"leftReg=",leftReg,"rightReg=",rightReg)
                
            return ('int',None,"BinaryOp",None) # Up to the Assign node to add code to put A register to correct memory location

        elif node_type=="ID":
            #if statement.name not in variables:
            if not self.variables.contains(self.local_scope, statement.name):
                address = NextMemorySlot()
                # We should only do this if we're inheriting from a declaration node
                #print("Declaring new variable here",statement.name)
                var_type=None
                if "Decl" in self.inherit_dict:
                    var_type=self.inherit_dict["Decl"]
                self.variables.add(self.local_scope,statement.name,var_type,None,address)#[statement.name]=[None,None,address]
                #self.variables.add(self.local_scope,var_name,var_type,var_value,address)
                
            var_type = self.variables.get_type(self.local_scope,statement.name)#variables[statement.name][0]
            var_value = self.variables.get_value(self.local_scope,statement.name)#variables[statement.name][1]
            addr = self.variables.get_address(self.local_scope,statement.name)#variables[statement.name][2]
            regvalue = "["+formatNumber(addr)+"]"
            
            if loadReg:
                if not silent: self.addASM("mov "+loadReg+",["+formatNumber(addr)+"]")#self.ASMcode+="mov "+loadReg+",["+formatNumber(addr)+"]\n"
            
            return (var_type,None,"ID",statement.name,regvalue) # i.e. 'int',1,"ID",'a'
        
        elif node_type=="FileAST": # First node
            for si,s in enumerate(statement.ext):
                #print("********** STATEMENT **********",si)
                next_node_type=s.__class__.__name__
                #print(next_node_type)
                if next_node_type=="FuncDef":
                    funcname = s.decl.name
                    self.variables.add_scope(funcname)
                    
                    if funcname=="main":
#                        print("Walking main")
                        self.walkAST(s)
                        self.addASM("halt")  # end of main
                    else:
                        #print("Skipping function:",funcname)
                        self.FuncASTlist.append(s)
                else:
                    self.walkAST(s)
                    
        elif node_type=="FuncDef":
    ##        print(statement)
    ##        print("Walking function:",statement.decl.name)
    ##        print("...")
            self.local_scope = statement.decl.name
            self.walkAST(statement.decl)

            for bi,b in enumerate(statement.body):
                #print("##### Body statement",bi," #####")
                self.walkAST(b)

        elif node_type=="FuncDecl":
            args = statement.args
            var_type=self.walkAST(statement.type)[0]
            return ((args,var_type),"FuncDecl")

        elif node_type=="DoWhile":
            label0 = new_label("enter_dowhile",increment=False)
            self.addASM(label0+":")
            for s in statement.stmt:
                self.walkAST(s)

            self.walkAST(statement.cond,loadReg="A") # if conditional is TRUE, A = 0x01
            self.addASM("cmp A,0x00")
            self.addASM("jnz "+label0)
            
        elif node_type=="While":
            
            label0 = new_label("enter_while",increment=False)
            label1 = new_label("exit_while")

            self.addASM(label0+":")
            cond = self.walkAST(statement.cond,loadReg="A")

            self.addASM("cmp A,0x00")
            self.addASM("jz "+label1)
            for s in statement.stmt:
                self.walkAST(s)

            self.addASM("jmp "+label0)
            self.addASM(label1+":")
            
        elif node_type=="UnaryOp":
            if self.verbose: print(statement)

            unaryReg = "A"
            if loadReg!=None: unaryReg=loadReg
            details = self.walkAST(statement.expr,unaryReg) # i.e.
            op = statement.op
               
            if loadReg=="A" or loadReg==None:
                status_reg = getReg() # we will use a new register - when is this freed...?
            else:
                status_reg = loadReg # we can put result straight in report register
                if loadReg!=None and (op=="p++" or op=="p--"):
                    self.addASM("push A")
                    self.addASM("mov A,"+loadReg)

            if op in conditionals:
                cond_label = new_label("cond")
                
                self.addASM("mov "+status_reg+",0x01")
                # We can only CMP with register A
                self.addASM("cmp A,0x00") # I think cmp A,0x00 is not strictly needed for jz and jnz?          
                
                condcode = conditionals[op] # !: jnz
                self.addASM(condcode+" "+cond_label)
                self.addASM("mov "+status_reg+",0x00")
                self.addASM(cond_label+":")
                
                if loadReg!=status_reg:
                    self.addASM("mov "+loadReg+","+status_reg)
                    freeReg(status_reg)
                loadReg = None
                
                return ('int',None,"BinaryOp",None) # I think it's okay to return type as BinaryOp...
            elif op=="p++":
                self.addASM("inc A")
                # we need to return A to the
                self.addASM("mov "+details[4]+",A")
                if loadReg!="A" and loadReg!=None:                    
                    self.addASM("mov "+loadReg+",A")
                    self.addASM("pop A")
            elif op=="p--":
                self.addASM("dec A")
                self.addASM("mov "+details[4]+",A")
                if loadReg!="A" and loadReg!=None:
                    self.addASM("mov "+loadReg+",A")
            else:
                print("Unsupported UnaryOp:",op)

            return details
                            
        elif node_type=="If":
            iftrue = new_label("ifTrue",increment=False)
            iffalse = new_label("ifFalse",increment=False)
            ifend = new_label("ifEnd")
            
            cond = self.walkAST(statement.cond,loadReg="A")
            self.addASM("cmp A,0x00")
            self.addASM("jz "+iffalse)

            self.addASM(iftrue+":")# Just for readability
            for s in statement.iftrue: # True path here
                self.walkAST(s)

            if statement.iffalse!=None:
                self.addASM("jmp "+ifend) # Jump over ifFalse code
                
            self.addASM(iffalse+":")
            if statement.iffalse!=None:
                self.walkAST(statement.iffalse)
                self.addASM(ifend+":")

        elif node_type=="Compound":
            for s in statement.block_items:
                self.walkAST(s)
        elif node_type=="Pragma":
            # usage 0,1 or 2 parameters:
            # #pragma asm("mov A,B")
            # #pragma asm("mov %0,A",c)
            # #pragma asm("mov %0,%1",c,0x01)
            
            asm_match = re.match('asm\("(.*)"\)',statement.string)
            if asm_match:
                self.addASM(asm_match.group(1))
                return

            asm_match = re.match('asm\("(.*)",(.*),(.*)\)',statement.string)
            if asm_match:
                asm = asm_match.group(1)
                first = asm_match.group(2)
                second = asm_match.group(3)
                
                first = self.variables.reference(self.local_scope,first)
                second = self.variables.reference(self.local_scope,second)
                
                asm=asm.replace("%0",first)
                asm=asm.replace("%1",second)
                
                self.addASM(asm)
                return

            asm_match = re.match('asm\("(.*)",(.*)\)',statement.string)
            if asm_match:
                asm = asm_match.group(1)
                first = asm_match.group(2)
                first = self.variables.reference(self.local_scope,first)           
                asm=asm.replace("%0",first)

                self.addASM(asm)
                return
            #re.match('asm\(".*"\)',a)
        elif node_type=="For":
            #print(statement)
            # init
            # startfor:
            #   test condition
            #   if false, jump to endfor
            #   statements
            #   next
            #   jmp startfor
            # endFor:
            self.walkAST(statement.init)
            startfor = new_label("startFor",increment=False)
            endfor = new_label("endFor")

            self.addASM(startfor+":")
            cond = self.walkAST(statement.cond)

            self.addASM("cmp A,0x00")
            self.addASM("jz "+endfor)
            
            for s in statement.stmt:
                self.walkAST(s)

            self.walkAST(statement.next)
            self.addASM("jmp "+startfor)
            self.addASM(endfor+":")
            
        elif node_type=="DeclList":
            for d in statement.decls:
                self.walkAST(d)
        else:
            print("I don't understand how to parse Class name:",node_type)
            return None

label_number=0
all_labels = []
def new_label(labeltext="label",increment=True,no_number=False):
    global label_number
    if no_number:
        label=labeltext
    else:
        label = labeltext+str(label_number)

    label=label.replace("_","") # '_' confuses regular expressions used in assembler...
    if increment: label_number+=1

    if label not in all_labels: all_labels.append(label)
    else: print("ERROR! Label is not unique:",label)
    return label

if __name__=="__main__":
    text=r"""
    int var69=69;
    int hello=world=3;
    int f = 2;
    int a = 1+2;
    int b = a+f+3;
    int g = f+(2+3);
    int h = (1+2)+3;
    int i = j=((a-9)+(2+5))+((3+0)+(4+250));

    void function(void)
    {
        a=0;
    }

    int q = 5;
    
    void main()
    {
        int c=0;

        while((b < c) || (g<h))
        {
            c=c+1;
            a=g+f;
            if (a>b)
            {
            b=b+1;
            }
            else if (a==10)
            {
            b=10;
            }
            else if ((a+f)!=255)
            {
            f = f + 42;
            }
            else
            {
            if ((!(c+23)) && !b){
                a=b=32;
            }
            }
            a=(2+3)+(b+5);
        }
        a=(2+3)+b;

        f=f+1;
        
        for (int cc=0;cc<100;cc=cc+1)
        {
            #pragma asm("test")
        }
        
       
      
    }

    void putchar(int c)
    {
    int c=23;
    #pragma asm("mov A,B")
    #pragma asm("mov U,%0",c)
    #pragma asm("mov %0,%1",c,0x01)
    }
    """
    import optimise_asm
    from optimise_asm import Optimiser
    mycompiler = Compiler()
    ASMcode = mycompiler.compile(text,verbose=False) 

    print(ASMcode)

    asmOptimiser = Optimiser(temp_regs)
    opt_code = asmOptimiser.optimise_code(ASMcode)
    print(opt_code)
    
