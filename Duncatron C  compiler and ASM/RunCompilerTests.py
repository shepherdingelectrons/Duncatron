import Duncatron_C_compiler
from optimise_asm import Optimiser
from simple_assembler import Assembler
import CPUSimulator.CPU as CPU

import glob
import pickle

class TestPipeline:
    def __init__(self, logfile,cfolder,asmfolder,clearOutputs=False):
        self.logfile = logfile
        self.correct_outputs = {} # Dictionary of filename keys and correct outputs
        self.c_files = []
        self.asm_files = []
        self.clearOutputs = clearOutputs

        self.ScanForCFiles(cfolder)
        self.ScanForASMFiles(asmfolder)
        self.readLogFile()

    def readLogFile(self):
        if glob.glob(self.logfile):
            print("Log file found")
            fileObj = open(self.logfile, 'rb')
            try:
                self.correct_outputs = pickle.load(fileObj)
            except:
                pass
            fileObj.close()     
        else:
            print("Log file not found, creating")
            
    def writeLogFile(self):
        fileObj = open(self.logfile, 'wb')
        pickle.dump(self.correct_outputs,fileObj)
        fileObj.close() 
            
    def ScanForCFiles(self, folder):
        self.c_files = glob.glob('./'+folder+'/*.txt')

    def ScanForASMFiles(self, folder):
        self.asm_files = glob.glob('./'+folder+'/*.txt')

    def RunTests(self):
        # Could/should add ASM file test ability
        error_log = {}
        for cfile in self.c_files:
            error_log[cfile]=self.RunCFile(cfile)

        self.writeLogFile()
        self.printTestSummary(error_log)

    def printTestSummary(self,error_log):
        decor = "*"*21
        banner= decor + " Pipeline test summary "+decor
        print("\n\n"+banner)
        
        for file in error_log:
            std_err, opt_err = error_log[file]
            std_err_str = "PASS" if std_err else "FAIL"
            opt_err_str = "PASS" if opt_err else "FAIL"

            file = file.split('\\')[-1]
            error_str = file+";\t standard ASM:"+std_err_str+", optimised ASM:"+opt_err_str
            print(error_str)
        print("*"*len(banner)+"\n\n")
        input("PRESS ENTER TO EXIT")

    def queryUser(self,prompt,filehandle,output):
        answer = input(prompt).upper()
        if answer=="" or answer=="Y":
            self.correct_outputs[filehandle] = output
            return True
        return False
    
    def handleOutput(self,filehandle,output):
        if filehandle not in self.correct_outputs or self.clearOutputs:
            # If we are here then this is a new file or the clearOutputs flag is set
            print("Output for: '"+filehandle+"' is:")
            print(output)
            
            if not self.queryUser("Is the output correct? Y/n",filehandle,output):
                self.correct_outputs[filehandle] = None # None means undefined for now
                return None
            else:
                return True
        else:
            if self.correct_outputs[filehandle]==output:
                print("Output check: PASS")
                return True
            else:
                print("Expected output is:")
                print(self.correct_outputs[filehandle])
                
                print("Output for: '"+filehandle+"' is:")
                print(output)
                print("ERROR: Output for '"+filehandle+"' does not match previous")
                
                if self.correct_outputs[filehandle]==None:
                    if not self.queryUser("Accept this new output? Y/n",filehandle,output):
                       return None
                return False
        
    def RunCFile(self,filename):
        print("***** OPENING :",filename,"*****")
        c_file = open(filename)
        text = c_file.read()
        c_file.close()

        standard_error = True 
        optimised_error = True
        
        mycompiler = Duncatron_C_compiler.Compiler()
        ASMcode = mycompiler.compile(text,verbose=False)
        std_output = self.AssembleAndSimulate(ASMcode)
        standard_error = self.handleOutput(filename,std_output)
        print("STD:",standard_error)
 
        asmOptimiser = Optimiser(Duncatron_C_compiler.temp_regs)
        optimised_ASMcode = asmOptimiser.optimise_code(ASMcode)
        opt_output = self.AssembleAndSimulate(ASMcode)

        if std_output!=opt_output:
            print("Error: optimised-asm CPU output is different to standard-asm CPU output")
            optimised_error = False
        else:
            print("Optimised assembly matches standard assembly output: PASS")

        return (standard_error,optimised_error)

    def AssembleAndSimulate(self,asm_text):
        CPU.reset() # wipes memory (by default) and restores state
        asm = Assembler(None,CPU.Memory,asm_text) # We pass on the CPU Memory so that
        # the machine code can be put into it for simulation

        if asm.assemble():
            print("Simulating...")
            uart_out=""
            while not CPU.HALT.isactive(None):
                CPU.CPU.compute()
                if CPU.U_reg.value!=-1:
                        uart_char = chr(CPU.U_reg.value)
                        uart_out +=uart_char
                        CPU.U_reg.value=-1
            return uart_out
        else:
            print("ERROR: Bad assembly generated!")
            return False

testing = TestPipeline("logfile.txt","c files","asm files",False)
testing.RunTests()
