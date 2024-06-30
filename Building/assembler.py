def asm(line):
        # This is intentionally written in non-pythonic way, to
    # evaluate the algorithm that will be used on an 8-bit homebrew computer

    if line==None:
        return None
    length = len(line)
    output = [None,None,None,None]

    if length==0:
        print("Zero length line, ignored")
        return

    opnum = 0
    a = 0
    while a<len(instruction_str): # loop over instruction string
        #testop = instruction_str[a]
        invalid_opcode = 0
        output = [opnum,None,None,None] # Reset machine code translation for each test
        # Go through each character in the line and test against each opcode format to find a match
        
        firstdigit = 0
        opsum = 0
        oppos = 1 # First operand position
        endpos = 255 # impossible value, means no endpos set
        i=0
        
        while endpos==255:
            d = instruction_str[a+i].upper() #testop[i].upper()
            
            if i<length:
                c = line[i].upper()
            else:
                #invalid_opcode = 1
                c='#'           

            # Now do some pattern matching and find various ways of invalidating match
##            if opnum==221:
##                print(c,d,a,i)
            
            if d=='#': # found end of opcode format
                #print("end char")
                #break # break from i loop
                if endpos == 255:
                    endpos = i
                if length>i:
                    invalid_opcode = 1
            
            elif d=='@':
                valid=0
                if c>="0" and c<="9":
                    value = ord(c)-ord('0')
                    valid=1
                if c>="A" and c<="F":
                    value = 10+ord(c)-ord("A")
                    valid=1
                if c>="a" and c<="f":
                    value = 10+ord(c)-ord("a")
                    valid=1
                    
                if valid==1:
                    if firstdigit==0:    
                        opsum = value
                        firstdigit = 1
                    elif firstdigit==1:
                        opsum = 16*opsum # shift left four times
                        opsum += value
                        output[oppos] = opsum
                        oppos+=1
                        firstdigit = 0 #reset value building 
                else:
                    #print("invalid digit")
                    invalid_opcode = 1
            elif d=='~': # ignore tilde symbol and add padding byte
                output[oppos] = 0
                oppos+=1
            elif c!=d:
                invalid_opcode=1
            i+=1
            
        # If we get to the end of the line and match is not invalidated, then it is validated!
        if invalid_opcode==0:
            machine_code = "0x"+str(output[0]).format('02x')#format(output[0], '02x')
            if output[1]!=None:
                machine_code+=str(output[1]).format('02x')#format(output[1], '02x')
            if output[2]!=None:
                machine_code+=str(output[2]).format('02x')#format(output[2], '02x')
            if output[3]!=None:
                machine_code+=str(output[3]).format('02x')#+=format(output[3], '02x')
            
            #print(line,machine_code)
            
            return output
        a=a+endpos+1 # next opcode in string
        opnum+=1
        # next a loop
        
    # If we got here, there was no valid match
    print(line,":Invalid syntax!")
    return None

def lookupASM(I):
    for ins,string in enumerate(instruction_str.split("#")):
        if ins==I:
            return string
    return None

instruction_str = 'INC A#SUB A,0x@@#CMP A,0x@@#DEC A#ADDC A,0x@@#SUBC A,0x@@#CMPC A,0x@@#MOV A,U#INC B#MOV U,A#MOV U,B#DEC B#MOV B,U#MOV AB,0x@@@@#MOV A,B#MOV B,A#ADD A,r0#SUB A,r0#CMP A,r0#MOV U,0x@@#ADDC A,r0#SUBC A,r0#CMPC A,r0#MOV [r0r1],0x@@#MOV AB,r0r1#MOV AB,r2r3#MOV AB,r4r5#MOV A,r1#MOV B,r1#MOV A,0x@@#MOV A,[0x@@]#MOV A,[0x@@@@]#ADD A,r2#SUB A,r2#CMP A,r2#MOV [r2r3],0x@@#ADDC A,r2#SUBC A,r2#CMPC A,r2#MOV [r2r3],A#MOV A,r3#MOV B,r3#POP A#MOV B,0x@@#MOV B,[0x@@]#MOV B,[0x@@@@]#POP B#PUSH A#ADD A,r4#SUB A,r4#CMP A,r4#MOV [r4r5],0x@@#ADDC A,r4#SUBC A,r4#CMPC A,r4#MOV [r4r5],A#MOV A,r5#MOV B,r5#MOV [0x@@],A#MOV [0x@@@@],A#PUSH 0x@@#POP T#PUSH r5#MOV [0x@@],r5#ADD A,0x@@#SUB A,B#CMP A,B#MOV r0r1,AB#ADDC A,B#SUBC A,B#CMPC A,B#MOV r1,A#MOV r0r1,0x@@@@#MOV r0,A#MOV r0,B#MOV r0,0x@@#MOV r1,B#MOV r1,0x@@#MOV r1,[0x@@]#MOV r1,[0x@@@@]#INC r0#SUB A,r1#CMP A,r1#DEC r0#ADDC A,r1#SUBC A,r1#CMPC A,r1#MOV [r0r1],A#INC r1#MOV r0,r1#MOV r1,r0#DEC r1#INC r0r1#POP r1#PUSH r1#MOV [0x@@],r1#ADD A,r3#SUB A,r3#CMP A,r3#MOV r0r1,r2r3#ADDC A,r3#SUBC A,r3#CMPC A,r3#MOV A,[r2r3]#MOV r0,r3#MOV r1,r2#MOV r0,[0x@@]#MOV r0,[0x@@@@]#MOV r0,r2#MOV r1,r3#PUSH r3#MOV [0x@@],r3#ADD A,r5#SUB A,r5#CMP A,r5#MOV r0r1,r4r5#ADDC A,r5#SUBC A,r5#CMPC A,r5#MOV A,[r4r5]#MOV r0,r5#MOV r1,r4#POP r0#MOV [0x@@@@],r5#MOV r0,r4#MOV r1,r5#NOR A,B#RCL A#ADD A,B#MOV r2r3,AB#MOV r2r3,0x@@@@#MOV r2,A#MOV r3,A#RETI#MOV r3,0x@@#MOV r3,[0x@@]#MOV r2,B#MOV r2,0x@@#MOV r2,[0x@@]#MOV r2,[0x@@@@]#MOV r3,B#MOV r3,[0x@@@@]#POP r3#PUSH B#ADD A,r1#MOV A,[r0r1]#MOV r2r3,r0r1#MOV A,r0#MOV B,r0#MOV r3,r0#PUSH r0#MOV [0x@@],r0#MOV r2,r1#POP r2#MOV [0x@@@@],r1#OR A,B#MOV r2,r0#MOV r3,r1#NOR A,0x@@#MOV A,F#INC r2#MOV A,r2#MOV B,r2#DEC r2#MOV r3,r2#PUSH r2#MOV [0x@@],r2#MOV [0x@@@@],r2#INC r3#MOV r2,r3#MOV [0x@@@@],r3#DEC r3#INC r2r3#AND A,B#PUSH F#POP F#MOV r2r3,r4r5#MOV A,r4#MOV B,r4#MOV r2,r4#MOV r3,r4#PUSH r4#MOV [0x@@],r4#MOV [0x@@@@],r4#MOV r2,r5#XOR A,B#NAND A,B#OR A,0x@@#MOV r3,r5#AND A,0x@@#PUSH_PC+1#INT#MOV r4r5,AB#MOV r4r5,0x@@@@#MOV r4,A#MOV r4,0x@@#MOV r5,A#MOV r5,0x@@#MOV r5,[0x@@]#MOV r5,[0x@@@@]#MOV r4,B#MOV r4,[0x@@]#MOV r4,[0x@@@@]#POP r4#MOV r5,B#POP r5#MOV [0x@@],B#MOV [0x@@@@],B#MOV r4r5,r0r1#MOV r4,r0#MOV [0x@@@@],r0#JZ 0x@@@@#MOV r5,r0#JNZ 0x@@@@#JE 0x@@@@#NOT A#MOV r4,r1#XOR A,0x@@#NAND A,0x@@#JNE 0x@@@@#MOV r5,r1#JG 0x@@@@#JGE 0x@@@@#JL 0x@@@@#MOV r4r5,r2r3#MOV r4,r2#JLE 0x@@@@#JMP 0x@@@@#MOV r5,r2#JC 0x@@@@#JNC 0x@@@@#CLRC#MOV r4,r3#CALL_Z 0x@@@@#CALL_NZ 0x@@@@#CALL_E 0x@@@@#MOV r5,r3#CALL_NE 0x@@@@#CALL_G 0x@@@@#CALL_GE 0x@@@@#SHL A#CALL_L 0x@@@@#CALL_LE 0x@@@@#DEC r4#INC r4#MOV r5,r4#CALL 0x@@@@#CALL_C 0x@@@@#INC r5#MOV r4,r5#CALL_NC 0x@@@@#DEC r5#INC r4r5#RET#HALT#NOP#'
##asm("MOV B,0x20")
##asm("ADD A,B")
##asm("JMP 0x1234")
##
##print(asm("CALL 0x1200"))
##print(asm("CALL 0x1234"))

