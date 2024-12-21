import pygame

pygame.init()

class ConsoleEmulator:
    def __init__(self,charX=80,charY=36):        
        fontsize = 15
        self.font = pygame.font.SysFont("couriernew",fontsize)#Font(None, 20)
        w,h = self.font.size("A") # only works for monospaced fonts
        
        self.swidth = charX#w * 40
        self.sheight = charY#h * 30
        self.screen = pygame.display.set_mode((charX*w,charY*h))

        wincolour = (255,255,255)
        self.screen.fill(wincolour)
        
        self.fx = 0
        self.fy = 0
        self.CharMatrix = [[0 for x in range(0,self.swidth)] for y in range(0,self.sheight)]
        self.previousMatrix = [[0 for x in range(0,self.swidth)] for y in range(0,self.sheight)]
        self.quit = False
        self.Computer = None
        self.readQueue = []
        
    def connectCPU(self, Computer):
        self.Computer = Computer
        if self.Computer.console == None: # If console isn't connected, reciprocate
            self.Computer.connectConsole(self)

    def _printCharToConsole(self,char):
        # handles the screen scrolling and limits
        self.fx+=1
        if self.fx>=self.swidth:
            self.fx=0
            self.fy+=1
        
        if self.fy>=self.sheight:
            #  bump up image by h
            #self.fy = 0 # hack for now
            self.fy=self.sheight-1
            for row in range(0,self.sheight-1):
                self.CharMatrix[row]=self.CharMatrix[row+1]
            self.CharMatrix[self.sheight-1]= [0 for x in range(0,self.swidth)] # clear new final row

    def printToConsole(self,char):
        if char==13:
            self.fx=0
            return
        if char==10:
            self.fy+=1
            return

        if char==127:
            self.CharMatrix[self.fy][self.fx] = 0
            self.fx-=1
            if self.fx<0:
                self.fx=0
                print("shouldn't happen!")
            return
        
        if char==9: # deleting char characters properlycurrently not supported
            nexttab = ((self.fx>>2)+1)<<2
            for tx in range(self.fx,nexttab):
                self._printCharToConsole(0x20)
                #self.CharMatrix[self.fy][tx]=0x20 # space character
            self.fx=nexttab
            return

        self._printCharToConsole(char) # handles scrolling
        self.CharMatrix[self.fy][self.fx]=char

    def RenderConsoleMatrix(self):
        fg = 0,0,0 #250, 240, 230
        bg = 255,255,255#5, 5, 5
        w,h = self.font.size("A")
        
        for row in range(0,self.sheight):
            for col in range(0,self.swidth):
                character = self.CharMatrix[row][col]
                if character!=self.previousMatrix[row][col]:
                    self.previousMatrix[row][col] = character
                    if character==0: character=32 # Draw a space to blank our canvas
                    if character>31:
                        ren = self.font.render(chr(character), 0, fg, bg)
                        self.screen.blit(ren, (col*w, row*h))
            
##    def printchar(self,char, cx,cy,is_int=False): # expects char to be a byte
##        fg = 0,0,0 #250, 240, 230
##        bg = 255,255,255#5, 5, 5
##        w,h = self.font.size("A")
##
##        if is_int:
##            if char<31:
##                if char==13: self.fx=0
##                if char==10: self.fy+=h
##                return 0
##            char=chr(char)
##        
##        ren = self.font.render(char, 0, fg, bg)
##        self.screen.blit(ren, (cx, cy))
##
##        return w

##    def displayRegister(self,reg,rx,ry,num_format='08b'):
##        text = format(reg, num_format)
##        for c in text:
##            w = self.printchar(c,rx,ry)
##            rx+=w
   
    def pygame_handle(self):
        #self.VRAM()
##        self.displayRegister(CPU.A_reg.value,500,0)
##        self.displayRegister(CPU.B_reg.value,500,29)
##        self.displayRegister(CPU.F_reg.value,500,29*2)
##        self.displayRegister(CPU.PC.valueHI<<8|CPU.PC.value,500,29*3,'04x')
##        self.displayRegister(CPU.SP.valueHI<<8|CPU.SP.value,500,29*4,'04x')

        self.RenderConsoleMatrix()

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                #print(event.key)
                UART_RX = event.key
                if UART_RX<128: # politely ignore anything >127
                    if UART_RX == 13: # 0x0D = carriage return
                        UART_RX = 10 # remap return/line feed character
                    if UART_RX == 8:
                        UART_RX = 127 # remap backspace to delete
                    
                    # Send key by virtual UART
                    if self.Computer!=None:
                        self.write(chr(UART_RX))
                
            elif event.type == pygame.QUIT:
                self.quit=True
        return self.quit

    def write(self,char): # Write to Computer (TX-->Computer RX)
        UART_RX = ord(char)&0xFF
        self.Computer.U_reg.valueHI = UART_RX # Use U_reg.valueHI for RX
        self.Computer.F_reg.value|=(1<<4) # Set RX_READY

    def read(self): # Read from Computer (RX<--Computer TX)
        readChars = self.readQueue
        self.readQueue = []
        return readChars
    
    def close(self):
        pygame.quit()
