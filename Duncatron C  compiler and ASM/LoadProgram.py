import CPUSimulator.CPU as CPU
import simple_assembler
import serial

class DuncatronInterface:
    def __init__(self,port=None):

        self.asm = None
        self.myCPU = None
        self.myConsole = None
        self.port = None
        self.CPU_UP=False
        
        self.streamFile = None
        self.streamReady = False
        self.next_char = ""
        
        if port!=None:
            self.openSerial(port)
        else:
            self.initCPU()
    
    def initCPU(self):
        self.myCPU = CPU.Computer() 
        # *********************** ASSEMBLE CODE *******************************
        print("Assembling code:")
        self.asm = simple_assembler.Assembler("SystemOS.asm",self.myCPU.Memory)
        success = self.asm.assemble(show_labels = True)
        # *********************** EMULATE CPU *******************************
        if success:
            print("Assemble OK!")
            print("Emulating CPU:")
            import CPUSimulator.Console as Console

            self.myConsole = Console.ConsoleEmulator()
            self.myCPU.connectConsole(self.myConsole)
            self.myCPU.randomiseRAM(0x8000,0x10000)
            self.CPU_UP = True
        else:
            print("ERROR: Compiling code")

    def tick(self):
        if not self.CPU_UP:
            print("ERROR: No computer attached!")
            return

        if self.myCPU:
            if self.myCPU.HALT.isactive(None): self.CPU_UP = False
            self.myCPU.CPU.compute(verbose=False)#

        if self.myConsole.pygame_handle(): self.CPU_UP = False

        if self.myConsole.dropfile and self.streamFile==None:
            self.startStreaming(self.myConsole.dropfile)
            self.myConsole.dropfile=None

        if self.streamFile:
            self.DoStreaming()

    def startStreaming(self,filename):
        self.streamFile = open(filename,"rb") # open file
        self.streamReady = True
        self.myConsole.handleUART=False
        
    def DoStreaming(self):
        if self.streamReady:
            self.next_char = self.streamFile.read(1)
            if len(self.next_char)==0:
                self.stopStreaming()
                print("Streaming complete")
            else:
                self.next_char = ord(self.next_char) # convert to int
                self.myConsole.Computer.write(bytearray([self.next_char]))
                self.streamReady = False # wait for character to be returned
        else:
            chars = self.myConsole.Computer.read()
            if len(chars)>1:
                print("ERROR LEN CHARS > 1")
                self.stopStreaming()
                
            elif len(chars)==1:
                read_char = chars[0]
                self.myConsole.printToConsole(read_char)
                if self.next_char==read_char:
                    self.streamReady=True
                else:
                    print("Wrong read char!") # could add this as red text to myConsole
                    print("Expecting:",self.next_char,"Read:",read_char)
                    self.stopStreaming()
            
    def stopStreaming(self):
        self.streamFile.close()
        self.streamFile=None
        self.streamReady=False
        self.myConsole.handleUART=True
        print("Stopped file streaming")
        
    def openSerial(self,port):
##        serialPort = serial.Serial(
##    port="COM4", baudrate=9600, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE
##)
        try:
            self.port = serial.Serial(port,baudrate=38400,bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
        except serial.SerialException:
            print("ERROR: Serial port",port,"cannot be opened")
            return
        import CPUSimulator.Console as Console

        self.myConsole = Console.ConsoleEmulator()
        self.myConsole.connectPort(self.port)
        self.CPU_UP = True
        
    def close(self):
        if self.port:
            self.closeSerial()
            self.port=None
        if self.myCPU:
            self.myConsole.close()
            print("Final stack pointer=",self.myCPU.SP.value)
            self.myCPU = None

    def closeSerial(self):
        self.port.close()

# Initiate an interface to a console emulated computer (port=None)
# or a real computer on serial port specified
Duncatron = DuncatronInterface(port=None)

while Duncatron.CPU_UP:
    Duncatron.tick()
        
Duncatron.close()

    
