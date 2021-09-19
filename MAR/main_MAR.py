from pyb import Pin
import random

# Make Microsecond timer
def microwait(duration):
    micros.counter(0)
    while micros.counter()<duration:
        pass

# General Pin functionality
def setupPin(pinLabel, pinMode,active_low):
    # pinMode is Pin.OUT_PP or Pin.IN
    if active_low == True:
        PULL_UP_DOWN = Pin.PULL_UP # An active low pin, so pull_up to ensure pin is low by default
        initial_state = 1
    else:
        PULL_UP_DOWN = Pin.PULL_DOWN # active high pin, so use pull down resistors
        initial_state = 0
       
    p = Pin(pinLabel, pinMode, PULL_UP_DOWN)
    p.value(initial_state) # Sometimes, pull up/down resistors don'tt always seem to work for all pins to set an initial state
    return p

class PinBus():
    def __init__(self, name, buspinlabels):
        # Safest to initialise a bus to inputs rather than outputs
        self.buspinlabels = buspinlabels
        self.buspins = None
        self.setasinput()
        self.name = name
       
    def setasinput(self):
        self.buspins = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in self.buspinlabels]
           
    def setasoutput(self,value=None):
        self.buspins = [Pin(p, Pin.OUT_PP, Pin.PULL_DOWN) for p in self.buspinlabels]
        for p in self.buspins:
            p.value(0)

        if value!=None:
            self.value(value)
        
    def value(self, value):
        if self.buspins[0].mode()==Pin.IN:
            print("Warning: Data pins are not in OUTPUT mode")
        #print("Setting",self.name," to :",value)
        # First pin in list is LSB       
        for i,p in enumerate(self.buspins):
            p.value(1 if value&(1<<i) else 0)

    def getvalue(self):
        if self.buspins[0].mode()!=Pin.IN:
            print("Warning: Data pins are not in INPUT mode")
        val = 0
        for i,p in enumerate(self.buspins):
            val |= (p.value()<<i)
        return val

    def state(self):
        if self.buspins[0].mode()==Pin.IN:
            print("INPUT mode")
        else:
            print("OUTPUT mode")


def clockUP():
    CLK.value(1)
def clockDOWN():
    CLK.value(0)

def setMemoryAddress(value,zeropage=False):

    high = (value>>8) & 0xFF
    low = value & 0xFF
    
    if zeropage:
        # Although we can set the high data bus to the zeropage (0x8800) ourselves
        # this is a test that if we let it float, that it is pulled to the zeropage
        # address as this is how some instructions will use the zeropage
        if value>255: print("Warning zeropage address should be a single byte only")
        value=value&0xFF # ignore any top bits and treat address as 0-255
        high = 0x88# Zero page is 0x8800-0x88ff 
        databusHIGH.setasinput() # should be the case, but to be sure
        # High bus defaults to 0x88 with pull up/down resistors on bus
    else:
        databusHIGH.setasoutput()
        databusHIGH.value(high)
        
    databus.setasoutput()   
    databus.value(low)

    microwait(10)# let outputs settle
    MI.value(1)
    clockUP()
    microwait(10)
    clockDOWN()
    MI.value(0)

    # Set buses to inputs for safety
    databus.setasinput()
    databusHIGH.setasinput()

def off():
    databus.setasinput()
    databusHIGH.setasinput()
    
    MI.value(0)
    RI.value(0)
    RO.value(0)
    CLK.value(0)
    
def testaddr():
    for i in range(0,0xffff):
        setMemoryAddress(i)

def readMemory():
    databus.setasinput()
    
    RO.value(1)
    microwait(10) # let it settle
    clockUP()
    microwait(10)
    # read into pyboard here
    val = databus.getvalue()
    clockDOWN()
    RO.value(0)
    return val

def writeMemory(value):
    databus.setasoutput(value)
    RI.value(1)
    microwait(10)
    clockUP()
    microwait(100)
    clockDOWN()
    RI.value(0)
    databus.setasinput()

def peek(address,verbose=True,zeropage=False):
    setMemoryAddress(address,zeropage)
    if zeropage:
        address=0x8800|(address&0xff)
    val = readMemory()
    if verbose: print(hex(address),":",val,hex(val),bin(val))
    return val

def poke(address,value,zeropage=False):
    setMemoryAddress(address,zeropage)
    if zeropage:
        address=0x8800|(address&0xff)
    writeMemory(value)

def getRAND():
    r = int(random.random()*255)&0xff
    return r

def writetest(seed=0, wait=5000,writerange=range(0,0x100)):
    random.seed(seed) # reset random sequence with seed #0
    for addr in writerange:
        r = getRAND()
        poke(addr,r)
        #print(hex(addr),":",hex(r))
        if hex(addr)[-3:]=="000":
            print(hex(addr))
        microwait(wait)

def readtest(seed=0,readrange=range(0,0x100)):
    random.seed(seed) # reset random sequence with seed #0
    errors = 0
    tested=0
    for addr in readrange:
        r = getRAND()
        value = peek(addr,verbose=False)
        if hex(addr)[-3:]=="000":
            print(hex(addr))
        if r!=value:
            print(hex(addr),": READ:",value,"EXPECTED:",r)
            errors+=1
        tested+=1

    if errors:
        print("Errors:",errors)
    else:
        print("Memory test "+str(tested)+"/"+str(tested)+" OK")

import math

def prettyLEDs(redT=8,greenT=16,blueT=12):
    LEDi = lambda i,period,phase: int(abs(30*math.sin((math.pi*(phase+i)/period))))

    redT = 8+16*random.random()
    greenT = 8+16*random.random()
    blueT = 8 + 16*random.random()

    red_angle = 0
    blue_angle = 0
    green_angle = 0

    red_speed=random.random()
    green_speed=random.random()
    blue_speed=random.random()

    while True:
        red_angle += red_speed
        green_angle += green_speed
        blue_angle += blue_speed
        
        for i in range(0,16):
            green = LEDi(i,greenT,green_angle)
            red = LEDi(i,redT,red_angle)
            blue = LEDi(i,blueT,blue_angle)

            poke(0x8000+i*3,green)
            poke(0x8001+i*3,red)
            poke(0x8002+i*3,blue)
        
# Setup timers and pins here

# Assume first item is the LSB, last is the MSB
datapin_labels = ['X1','X2','X3','X4','X5','X6','X7','X8']
datapinHIGH_labels = ['X10','X9','Y8','Y7','Y6','Y5','Y4','Y3']

micros = pyb.Timer(2, prescaler=83, period=0x3fffffff)

MI = setupPin("X17", Pin.OUT_PP, active_low = False) 
RI = setupPin("X18", Pin.OUT_PP, active_low = False)
RO = setupPin("X19", Pin.OUT_PP, active_low = False)
CLK = setupPin("X22", Pin.OUT_PP, active_low = False)

databus = PinBus("low bus",datapin_labels)
databusHIGH = PinBus("high bus",datapinHIGH_labels)


