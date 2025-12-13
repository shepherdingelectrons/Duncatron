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

        self.fcol_default = (0,0,0)
        self.bcol_default = (255,255,255)
        
        self.fx = 0
        self.fy = 0
        self.CharMatrix = [[(0, self.fcol_default, self.bcol_default) for x in range(0,self.swidth)] for y in range(0,self.sheight)]
        self.previousMatrix = [[(0, self.fcol_default, self.bcol_default) for x in range(0,self.swidth)] for y in range(0,self.sheight)]
        self.quit = False
        self.Computer = None
        self.dropfile = None
        self.handleUART = True

        self.shift_map = {}
        self.init_shift_map()

    def init_shift_map(self):
        self.shift_map['1'] = '!'
        self.shift_map['2'] = '"'
        self.shift_map['3'] = '£'
        self.shift_map['4'] = '$'
        self.shift_map['5'] = '%'
        self.shift_map['6'] = '^'
        self.shift_map['7'] = '&'
        self.shift_map['8'] = '*'
        self.shift_map['9'] = '('
        self.shift_map['0'] = ')'
        self.shift_map['-'] = '_'
        self.shift_map['='] = '+'
        self.shift_map['['] = '{'
        self.shift_map[']'] = '}'
        self.shift_map[';'] = ':'
        self.shift_map["'"] = '@'
        self.shift_map['#'] = '~'
        self.shift_map['\\'] = '|'
        self.shift_map[','] = '<'
        self.shift_map['.'] = '>'
        self.shift_map['/'] = '?'

        for char in range(ord('a'),ord('z')):
            self.shift_map[chr(char)] = chr(char - 32)
      
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
            self.CharMatrix[self.sheight-1]= [(0,self.fcol_default,self.bcol_default) for x in range(0,self.swidth)] # clear new final row

    def printConsoleString(self,string,suffix="\n\r"):
        # Print to console and highlight with colour to show it is not output the computer
        print(string,end=suffix)
        string+=suffix
        for char in string:
            self.printToConsole(ord(char),((255,0,0),(255,255,255)))
        
                                
    def printToConsole(self,char,colour=None):
    
        if char==13:
            self.fx=0
            return
        if char==10:
            self.fy+=1
            return

        if char==127:
            self.CharMatrix[self.fy][self.fx] = (0,0,0)
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
        if colour:
            fg,bg=colour
        else:
            fg,bg=self.fcol_default,self.bcol_default
        self.CharMatrix[self.fy][self.fx]=(char,fg,bg)

    def RenderConsoleMatrix(self):
        fg = self.fcol_default #0,0,0 #250, 240, 230
        bg = self.bcol_default # 255,255,255#5, 5, 5
        w,h = self.font.size("A")
        
        for row in range(0,self.sheight):
            for col in range(0,self.swidth):
                character,fg,bg = self.CharMatrix[row][col]
                prev_char,_,_ = self.previousMatrix[row][col]
                
                if character!=prev_char:
                    self.previousMatrix[row][col] = (character,fg,bg)
                    if character==0:
                        character=32 # Draw a space to blank our canvas
                        fg = self.fcol_default
                        bg = self.bcol_default
                    if character>31:
                        ren = self.font.render(chr(character), 0, fg, bg)
                        self.screen.blit(ren, (col*w, row*h))
            
    def show_value(self,value,x,y):
        px = x
        py = y
        w = 10
        h = 10
        BLUE = (0,0,255)
        PALE_BLUE = (200,200,255)
        
        for n in range(0,8):
            bit = 7-n
            COLOUR = PALE_BLUE
            if value & (1<<bit):
                COLOUR=BLUE
            pygame.draw.rect(self.screen,COLOUR,(px,py,w,h))
            px+=w+1
            
    def pygame_handle(self):

        self.RenderConsoleMatrix()

##        if self.Computer:
##            self.show_value(self.Computer.Memory[0x8011],500,0)
##            self.show_value(self.Computer.Memory[0x8014],500,11)
##            self.show_value(self.Computer.Memory[0x8017],500,22)
##            self.show_value(self.Computer.Memory[0x801A],500,33)
##            self.show_value(self.Computer.Memory[0x801D],500,44)
##            
##            self.show_value(self.Computer.Memory[0x8021],500,55)
##            
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

                    # Check SHIFT status
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        print("shifting")
                        shiftkey = chr(UART_RX)
                        if shiftkey in self.shift_map:
                            UART_RX = ord(self.shift_map[shiftkey])
                    
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
