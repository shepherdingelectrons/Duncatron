from pyb import Pin
import random

# Assume first item is the LSB, last is the MSB
datapin_labels = ['X1','X2','X3','X4','X5','X6','X7','X8']
addrpin_labels = ['Y3','Y4','Y5','Y6','Y7','Y8','X9','X10','X11','X12']

datapinMode = -1 # Not set

class MemoryAccess():
    def __init__(self, CEpin, READwritepin,OE):
        self.CE = Pin(CEpin, Pin.OUT_PP, Pin.PULL_UP)
        self.chipDisable()

        # High initialisation seems not to work
        # - use an external pull-up 10k resistor?
        self.READwritepin = Pin(READwritepin, Pin.OUT_PP, pull=Pin.PULL_UP) 
        self.READwritepin.value(1) # Read = High, Write = active low.

        self.OE = Pin(OE, Pin.OUT_PP, Pin.PULL_UP)
        self.OE.value(1) # no output by default
        
    def chipEnable(self):
        self.CE.value(0)
    def chipDisable(self):
        self.CE.value(1)

    def write(self,addr,data):
        self.OE.value(1) # Disable output from memory chip
        
        if datapinMode!=Pin.OUT_PP: #Set pyboard datapins as output if necessary
            print("Setting pins as output")
            datapins = setup_datapins()
        
        setaddr(addr)
        setdata(data)
        self.READwritepin.value(0)
        microwait(1) # probably 100 ns would be fine
        self.READwritepin.value(1) # Always leave high

    def read(self,addr):
        self.READwritepin.value(1)
 
        if datapinMode!=Pin.IN: #Enable pyboard datapins as inputs
            print("Setting pins as inputs")
            datapins = setup_datapins(output=0)

        self.OE.value(0) # ENABLE output only once datapins on pyboard
        #have been set as inputs

        datapins = setup_datapins(output=0)
        setaddr(addr)
        microwait(1)
        return getdata()

def setup_addrpins():
    return [Pin(p, Pin.OUT_PP) for p in addrpin_labels]

def setup_datapins(output=True):
    global datapinMode
    # pinmode = Pin.OUT_PP or Pin.IN
    datapinMode = Pin.OUT_PP if output else Pin.IN
    return [Pin(p, datapinMode, Pin.PULL_DOWN) for p in datapin_labels]   

def setpins(pins, value):
    # First pin in list is LSB
    for i,p in enumerate(pins):
        p.value(1 if value&(1<<i) else 0)
            
def getpins(pins):
    val = 0
    for i,p in enumerate(pins):
        #print(i,p.value())
        val |= (p.value()<<i)
    return val
    
def setdata(value):
    if datapins[0].mode()==Pin.IN:
        print("Warning: Data pins are not in OUTPUT mode")
    setpins(datapins, value&255)

def getdata():
    if datapins[0].mode()!=Pin.IN:
        print("Warning: Data pins are not in INPUT mode")
    return getpins(datapins)

def getaddr():
    return getpins(addrpins)

def setaddr(value):
    setpins(addrpins, value)

def microwait(duration):
    micros.counter(0)
    while micros.counter()<duration:
        pass

def flashRAM(value):
    #LED_CE.value(1) #Disable LED display
    RAM.chipEnable()
    for i in range(1,1024):
        RAM.write(i,value)
    RAM.chipDisable()
    #LED_CE.value(0) #Enable LED display

def randomRAM():
    for i in range(0,1024):
        RAM.write(i,int(255*random.random()))

def clearRAM():
    for i in range(0,1024):
        RAM.write(i,0)

def setRAM():
    for i in range(0,1024):
        RAM.write(i,255)

# Setup timers and pins here
micros = pyb.Timer(2, prescaler=83, period=0x3fffffff)
addrpins = setup_addrpins()
datapins = setup_datapins()

print("Number of DATA pins:",len(datapins))
print("Number of ADDR pins:",len(addrpins))

LED_CE = Pin('X17', Pin.OUT_PP, pull=Pin.PULL_UP)
LED_CE.value(0)


RAM = MemoryAccess(CEpin='Y10',READwritepin='Y12', OE='Y11')
RAM.chipEnable()

LED_CE.value(1) # Might be needed or not for bus arbitration, not 100% sure.
microwait(1000000)
LED_CE.value(0)

import math

def displayImage(image,scale=0.5):
    # image is a bytearray
    for i in range(0,256*3):
        b = image[i]*scale
        b = int(b)
        RAM.write(i,int(b))


import RAMimages

displayImage(RAMimages.rainbow_square)
