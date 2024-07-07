ROMsize=32 # 16 instructions * 2 Carry-flag states = 32

ROM = bytearray([0x00]*ROMsize)

def AddCommand(instruction, control, mode, Cin):
    # address is comprised of:
    # FLAG-C, I3, I2, I1, I0
    #
    # Cin = 3 means use Cin = NOT(FLAG-Carry)
    # Cin = 2 means use Cin = FLAG-Carry
    # Cin = 1 means Cin = HIGH
    # Cin = 0 means Cin = 0

    # Byte format:
    #   7   6   5   4   3   2   1   0
    #   x   x   Cin M   C3  C2  C1  C0
    
    addr_CL = instruction & 0x0F
    addr_CH = (instruction & 0x0F) | (1<<4)

    output = (control & 0x0F) | (mode<<4)
    if Cin==2:
        ROM[addr_CL] = output | (0<<5)
        ROM[addr_CH] = output | (1<<5)
    elif Cin==3:
        ROM[addr_CL] = output | (1<<5)
        ROM[addr_CH] = output | (0<<5)
    else:
        ROM[addr_CL] = output | (Cin<<5)
        ROM[addr_CH] = output | (Cin<<5)

# New ALU command set:
#ALU_INSTRUCTIONS = ["ADD A,B","SUB A,B","CMP A,B","DEC A",
#"ADDC A,B","SUBC A,B","CMPC A,B","NOT A",
#"SHL A","XOR A,B","NAND A,B","OR A,B",
#"INC A","AND A,B", "NOR A,B", "RCL A"]

AddCommand(0, 0b1001, 0, 1) # ADD A,B
AddCommand(1, 0b0110, 0, 0) # SUB A,B
AddCommand(2, 0b0110, 0, 0) # CMP A,B
AddCommand(3, 0b1111, 0, 1) # DEC A
AddCommand(4, 0b1001, 0, 2) # ADDC A,B
AddCommand(5, 0b0110, 0, 2) # SUBC A,B
AddCommand(6, 0b0110, 0, 2) # CMPC A,B
AddCommand(7, 0b0101, 1, 1) # NOT A
AddCommand(8, 0b1100, 0, 1) # SHL A
AddCommand(9, 0b0110, 1, 1) # XOR A,B
AddCommand(10, 0b0100, 1, 1) # NAND A,B
AddCommand(11, 0b1110, 1, 1) # OR A,B
AddCommand(12, 0b1001, 0, 1) # INC A (uses ADDC ALU settings)
AddCommand(13, 0b1011, 1, 1) # AND int
AddCommand(14, 0b0001, 1, 1) # NOR int
AddCommand(15, 0b1100, 0, 2) # RCL = 2A+Flag_Carry

# Previous ALU command set:
##AddCommand(0, 0b0000, 1, 1) # NOT
##AddCommand(1, 0b0001, 1, 1) # NOR int
##AddCommand(2, 0b0100, 1, 1) # NAND int
##AddCommand(3, 0b0101, 1, 1) # NOT int
##AddCommand(4, 0b0110, 1, 1) # XOR int
##AddCommand(5, 0b0110, 0, 0) # SUB int
##AddCommand(6, 0b0110, 0, 2) # SUBC int
##AddCommand(7, 0b1001, 0, 1) # ADD int
##AddCommand(8, 0b1011, 1, 1) # AND int
##AddCommand(9, 0b1100, 0, 1) # SHL (A+A)
##AddCommand(10, 0b1110, 1, 1) # OR int
##AddCommand(11, 0b1111, 0, 1) # DEC
##AddCommand(12, 0b1100, 0, 2) # RCL = 2A+Flag_Carry
##AddCommand(13, 0b0011, 1, 1) # CLR (A=0)
##AddCommand(14, 0b1001, 0, 2) # ADDC int
##AddCommand(15, 0b0110, 0, 0) # CMP int

for i in range(0,16):
	print(i,bin(ROM[i]),bin(ROM[i+16]))

size=len(ROM)
binfilename = "ALU.rom"
print("Burning ALU rom..."+binfilename+" size:"+str(size)+" bytes")
f = open(binfilename,"wb")
f.write(ROM[0:size])
f.close()
##print("Binary written")
##f = open("ALU.py","w")
##f.write("ROM="+str(ROM)+"\n")
##f.close()
