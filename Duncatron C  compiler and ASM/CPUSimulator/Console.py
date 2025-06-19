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
        self.dropfile = None
        self.handleUART = True
##        self.readQueue = []
        
    def connectCPU(self, Computer):
        self.Computer = Computer
        if self.Computer.console == None: # If console isn't connected, reciprocate
            self.Computer.connectConsole(self)

    def connectPort(self, Port):
        self.Computer = Port
        
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
            
   
    def pygame_handle(self):

        self.RenderConsoleMatrix()

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                #print(event.key)
                UART_RX = event.key
                if UART_RX<128: # politely ignore anything >=128
                    if UART_RX == 13: # 0x0D = carriage return
                        UART_RX = 10 # remap return/line feed character
                    if UART_RX == 8:
                        UART_RX = 127 # remap backspace to delete
                    
                    # Send key by virtual UART
                    if self.Computer!=None and self.handleUART:
                        self.Computer.write(bytearray([UART_RX]))
                
            elif event.type == pygame.QUIT:
                self.quit=True
            elif event.type == pygame.DROPFILE:
                self.dropfile=event.file

        if self.Computer!=None and self.handleUART:
            chars = self.Computer.read()
            if len(chars):
                for read_char in chars:
                    self.printToConsole(read_char)
                
        return self.quit
    
    def close(self):
        pygame.quit()
