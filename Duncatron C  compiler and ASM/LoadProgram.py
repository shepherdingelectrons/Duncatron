import CPUSimulator.CPU as CPU
import simple_assembler
import serial
import os

class DuncatronInterface:
    NOT_STREAMING = 0
    FS_WAITING =    1
    FS_NEXT = 2

    SENDER = 0
    RECEIVER = 1
    FILE_STREAM = 2
    
    def __init__(self,port=None):

        self.asm = None
        self.myCPU = None
        self.myConsole = None
        self.port = None
        self.CPU_UP=False
        
        self.streamFile = None
        self.streamStatus = self.NOT_STREAMING
        self.streamIndex = 0
        self.next_char = ""
        self.streamErrors = 0
        self.filename = None
        self.prev_role = None
        self.load_address = 0

        self.StreamSeq = []

        self.defineStreaming()
        
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
            self.myCPU = None

    def tick(self):
        if not self.CPU_UP:
            print("ERROR: No computer attached!")
            return

        if self.myCPU:
            if self.myCPU.HALT.isactive(None): self.CPU_UP = False
            self.myCPU.CPU.compute(verbose=False)#

        if self.myConsole.pygame_handle(): self.CPU_UP = False

        if self.myConsole.dropfile:
            print(self.myConsole.dropfile,self.streamStatus)
            if self.streamStatus==self.NOT_STREAMING:
                print("Did we get here??")
                self.startStreaming(self.myConsole.dropfile)
                self.myConsole.dropfile=None

        self.DoStreaming()

    def addStreamSequence(self,role,send=None,receive=None,echo=False,run_function=None):
        if role==self.SENDER:
            if send==None:
                print("ERROR: Sender needs a send character!")
                return
            if echo==True:
                receive = send
            else:
                if receive == None:
                    print("ERROR: receive must be set if echo is False")
                    return
                
        if role==self.RECEIVER:
            if echo==True:
                send = True
            else:
                if receive == None:
                    print("ERROR: send character must be set if echo is False")
                    return
        
        self.StreamSeq.append([role,send,receive,run_function])
                       
    def defineStreaming(self):
        #self.addStreamSequence(role.self.SENDER,send="load 0x8300\n",echo=True)
        self.addStreamSequence(role=self.SENDER,send=chr(0x0A),receive=chr(0xA0)) # detect if not in command prompt
        self.addStreamSequence(role=self.SENDER,send=chr(0x55),receive=chr(0xAA))
        self.addStreamSequence(role=self.SENDER,send=chr(0xAA),receive=chr(0x55))
        self.addStreamSequence(role=self.RECEIVER,echo=True,run_function=self.setHighAddress)    # High byte of address
        self.addStreamSequence(role=self.RECEIVER,echo=True,run_function=self.setLowAddress)    # Low byte of address
        self.addStreamSequence(role=self.RECEIVER,receive='@',echo=False,run_function=self.OpenFile)    # ACK byte
        self.addStreamSequence(role=self.SENDER,send=chr(0x00),echo=True) # High of num bytes to send
        self.addStreamSequence(role=self.SENDER,send=chr(0x20),echo=True) # Low of num bytes to send
        self.addStreamSequence(role=self.FILE_STREAM,echo=True)


    def setHighAddress(self, read_char):
        self.load_address = read_char<<8

    def setLowAddress(self, read_char):
        self.load_address |= read_char
        
    def OpenFile(self,read_char):
        file, file_extension = os.path.splitext(self.filename)
        
        if file_extension == ".asm":
            self.myConsole.printConsoleString("Assembling code:")
            tempmemory = bytearray(0x10000)
            self.asm = simple_assembler.Assembler(self.filename,tempmemory,loadPOS=self.load_address)
            success = self.asm.assemble()
            if success:
                for lab in self.asm.labels:
                    self.myConsole.printConsoleString(lab+":"+hex(self.asm.labels[lab]))
                self.asm.burn_binary()
                self.myConsole.printConsoleString("Done")
                self.filename = file+".bin"
            else:
                self.myConsole.printConsoleString("Could not assemble!")
                self.stopStreaming()

        filesize = os.stat(self.filename).st_size
        self.streamFile = open(self.filename,"rb") # open file

        print("filesize = ",filesize)
        self.StreamSeq[6][1] = chr((filesize>>8)&0xff)
        self.StreamSeq[7][1] = chr(filesize&0xff)
        self.StreamSeq[6][2] = chr((filesize>>8)&0xff)
        self.StreamSeq[7][2] = chr(filesize&0xff)
        
    def startStreaming(self,filename):
        self.filename = filename
        self.streamStatus = self.FS_NEXT
        print("Self.streamStatus=",self.streamStatus)
        
        self.myConsole.handleUART=False
        self.myConsole.printConsoleString("Starting binary stream",suffix='')
        self.streamIndex = 0
        self.streamErrors = 0

    def DoStreaming(self):
        #self.myConsole.printConsoleString(str(self.streamIndex))
        
        if self.streamIndex>=len(self.StreamSeq):
            self.stopStreaming()
            #self.myConsole.printConsoleString("STOPPING")
            
        if self.streamStatus == self.FS_NEXT:
            role,send,receive,_ = self.StreamSeq[self.streamIndex]

            if role==self.SENDER:
                send_byte = send
                self.next_char = receive # Byte we are expecting to receive   

            elif role==self.RECEIVER:
                #self.myConsole.printConsoleString("Receiving byte")
                self.next_char = send
                #self.next_char = ord(self.next_char) # convert to int

            elif role==self.FILE_STREAM:
                #self.myConsole.printConsoleString("Starting file stream")
                    
                self.next_char = self.streamFile.read(1)
                send_byte = self.next_char

            if role==self.SENDER or role==self.FILE_STREAM:
                if len(self.next_char)==0:
                    self.stopStreaming()
                    self.myConsole.printConsoleString("Streaming complete, errors = "+str(self.streamErrors))
                else:
                    self.next_char = ord(self.next_char) # convert to int
                    
                    send_byte = ord(send_byte)
                    self.myConsole.Computer.write(bytearray([send_byte]))
                    #self.myConsole.printConsoleString(".",suffix='')
                    #self.myConsole.printConsoleString("Wrote byte"+hex(send_byte))

            if self.streamStatus!=self.NOT_STREAMING: self.streamStatus = self.FS_WAITING # wait for character to be returned
            self.prev_role = self.streamIndex

        elif self.streamStatus == self.FS_WAITING:
            #self.myConsole.printConsoleString("Checking for character...")
            role,send,receive,run_function = self.StreamSeq[self.streamIndex]
            
            chars = self.myConsole.Computer.read()
            if len(chars)>1:
                self.myConsole.printConsoleString("ERROR LEN CHARS > 1")
                self.stopStreaming()
                
            elif len(chars)==1:
                read_char = chars[0]
                #self.myConsole.printConsoleString("Byte received")
                #self.myConsole.printConsoleString(hex(read_char))
                
                if role==self.SENDER or role==self.FILE_STREAM:                    
                    if self.next_char==read_char:
                        #self.myConsole.printConsoleString("Character match!")
                        self.myConsole.printConsoleString(".",suffix='')
                        if role==self.SENDER:
                            self.streamIndex +=1
                        self.streamStatus = self.FS_NEXT
                        if run_function:
                            run_function(read_char)
                    else:
                        if role==self.SENDER:
                            self.stopStreaming()
                            self.myConsole.printConsoleString("Wrong read char!") # could add this as red text to myConsole
                            self.myConsole.printConsoleString(str(self.next_char))
                            self.myConsole.printConsoleString(str(read_char))
                        else:
                            self.streamErrors+=1
                            self.myConsole.printConsoleString("!",suffix='')
##                            self.myConsole.printConsoleString("Wrong read char!") # could add this as red text to myConsole
##                            self.myConsole.printConsoleString(str(self.next_char))
##                            self.myConsole.printConsoleString(str(read_char))
                            
                            self.streamStatus = self.FS_NEXT
                            
                elif role==self.RECEIVER:
                    #self.myConsole.printConsoleString(str(role)+str(send)+str(receive))
                    if send:
                        #rbyte = ord(read_char) # convert to int
                        self.myConsole.Computer.write(bytearray([read_char]))
                        #self.myConsole.printConsoleString("Wrote byte back"+hex(read_char))
                    if run_function:
                        run_function(read_char)
                        
                    self.streamStatus = self.FS_NEXT
                    self.streamIndex +=1
                    #self.myConsole.printConsoleString("Byte received")
                        
    def stopStreaming(self):
        if self.streamFile: self.streamFile.close()
        self.streamFile=None
        self.streamStatus=self.NOT_STREAMING
        print("Self.streamStatus=",self.streamStatus)
        self.myConsole.handleUART=True
        self.myConsole.printConsoleString("\n\rStopped file streaming")
        self.streamIndex = 0
        
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
Duncatron = DuncatronInterface(port=None) #"COM8")

while Duncatron.CPU_UP:
    Duncatron.tick()
        
Duncatron.close()

    
