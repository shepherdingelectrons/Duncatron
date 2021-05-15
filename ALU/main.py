# This python script runs on the pyboard v1.0 and writes the ALU data to the
# ALU EEPROM (AT28C16 Atmel EEPROM)

from pyb import Pin
import random

# Assume first item is the LSB, last is the MSB
datapin_labels = ['X1','X2','X3','X4','X5','X6','X7','X8']
addrpin_labels = ['Y3','Y4','Y5','Y6','Y7']

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
        microwait(1) # 1000 us = 1 ms
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

def write_image(device, image):
    for i,k in enumerate(image):
        device.write(i,k)
        print(i,k)
        microwait(10000) # Be generous and wait 10 ms for write to complete.
        # This can certainly be reduced, probably to 1 ms.

def check_image(device, image):
    flag=0
    for i,k in enumerate(image):
        r = device.read(i)
        print(i,":",r)
        if k!=r:
            print("ERROR at adddress:",i," expected: ",k," read: ",r)
            flag+=1
    if flag==0:
        print("Read OK!")
    print(flag," errors found")
    
# Setup timers and pins here
micros = pyb.Timer(2, prescaler=83, period=0x3fffffff)
addrpins = setup_addrpins()
datapins = setup_datapins()

print("Number of DATA pins:",len(datapins))
print("Number of ADDR pins:",len(addrpins))

EEPROM = MemoryAccess(CEpin='Y10',READwritepin='Y12', OE='Y11')
EEPROM.chipEnable()

import ALU # ALU.ROM is image

write_image(EEPROM, ALU.ROM) 
check_image(EEPROM, ALU.ROM)
