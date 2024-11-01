init:
	mov r0r1,INTERUPT; setup interrupt jump vector
	mov [0x00],r0	; Zero page 0x00
	mov [0x01],r1	; Zero page 0x01

	mov r0r1,ready	; Print a greeting message
	push_pc+1
	call print_str

; New string:
	mov r2r3,input_str
	mov r4,0x00
init.txwait:
	mov A,F ;128 64 32 16 8  4   2  1
		    ;F7  F6 SD RDY OF N  C  Z
	and A,0x20 ; TX SENDING
	jnz init.txwait
	
	mov U,0x3E ; ">"
	mov A,U ; clear uart register

; ################ main() ####################
main_loop:
	push_pc+1
	call handle_input	; returns r5=0 if no string, else r5=1
	mov A,r5
	cmp A,0x01
	jz main_loop.exe	; if an input is available, try and execute it
	jmp main_loop

main_loop.exe:
	push_pc+1
	call execute_cmd
	; check return code
	mov A,r4
	cmp A,0xff
	jz main.exit
	jmp main_loop
	
main.exit:
	mov r0r1,goodbye_str
	push_pc+1
	call print_str
	HALT
	jmp init ; If restart after HALT without reseting PC

; ###########################  Execute commands if matched #########################################
; ##############  r4 returns 0xff (non-zero) to exit main(), else r4 = 0 (doing nothing for now)  ##
execute_cmd:	
	mov r0r1,exit_str
	mov r2r3,input_str 
	push_pc+1
	call cmp_str
	mov A,r5
	cmp A,0x00
	jz execute_cmd.next0	; i.e. if r5 = 0 (no match)
	; 'exit' found
	mov r4,0xff		; r4!=0x00
	pop T
	ret
	;jz main.exit	; exit main loop and HALT
execute_cmd.next0:
	mov r0r1,program_str
	mov r2r3,input_str 
	push_pc+1
	call cmp_str
	mov A,r5
	cmp A,0x00
	jz execute_cmd.next1	; if r5 = 0 (no match)
	; 'prog' found
	push_pc+1
	call program_mode
	; would return here from program_mode if called
	mov r0r1,ready	; Print a greeting message
	push_pc+1
	call print_str
	
	jmp execute_cmd.exit

execute_cmd.next1:
; ... other programs here
execute_cmd.error:
; Else, command not found
; Throw an error
	mov r0r1,error_str
	push_pc+1
	call print_str

execute_cmd.exit:
	mov r2r3,input_str ; setup new input string
	mov r4,0x00
	execute_cmd.exit.TXWAIT:
		mov A,F
		and A,0x20
		jnz execute_cmd.exit.TXWAIT
	mov U,0x3E ; ">"

	pop T
	RET

; ########### Interupt vector ##################
INTERUPT:
RETI

;###### handle_input ###########################
handle_input:
mov A,F	;128 64 32 16 8  4   2  1
		;F7  F6 SD RDY OF N  C  Z
and A,0x10 ; RX character is waiting
jz handle_input.exit
mov A,U
cmp A,0x0A ; Return = 10 = 0x0A
jz handle_input.endstr; je
cmp A,0x7F ; backspace = 127 = 0x7F
jz handle_input.backchar
; other stuff here if not return char or backspace
; First compare there is room in string
push A
mov A,r4  ; compare r4 (length) to maximum length string
cmp A,0x80 ; 128 character limit for now
pop A
jz handle_input.exit ; maximum number of characters
; Handle character, put in memory etc

push A
handle_input.TXWAIT:
	mov A,F
	and A,0x20
	jnz handle_input.TXWAIT
pop A
mov U,A ; send character it back!
mov [r2r3],A
inc r2r3
inc r4 
jmp handle_input.exit

handle_input.backchar:
mov A,r4
cmp A,0x00 ; compare r4 to 0, if jz don't delete char else delete char
jz handle_input.exit

handle_input.TXWAIT0:
	mov A,F
	and A,0x20
	jnz handle_input.TXWAIT0
mov U,0x7F ; Send backspace to console
dec r4 
dec r3 ; decrease r2r3  pointer
mov A,r2
subc A,0x00
mov r2,A
jmp handle_input.exit

handle_input.endstr:
	mov A,F
	and A,0x20
	jnz handle_input.endstr
mov U,0x0A

handle_input.endstr1:
	mov A,F
	and A,0x20
	jnz handle_input.endstr1
mov U,0x0D
mov [r2r3],0x00 ; zero terminated string
;mov r0r1,input_str ; print string for now
;push_pc+1
;call print_str
mov A,r4
cmp A,0x00
jz handle_input.zerolen ; Don't do anything with zero length strings
mov r5,0x01 ; set r5 return register to true
pop T
RET

handle_input.zerolen:
mov r2r3,input_str ; setup new input string
mov r4,0x00
handle_input.zerolen.TXWAIT:
	mov A,F
	and A,0x20
	jnz handle_input.zerolen.TXWAIT
mov U,0x3E ; ">"

handle_input.exit:
mov r5,0x00
POP T
RET

;####  General helper function to compare two strings
;####  r0r1 pointer to zero-terminated string1
;####  r2r3 pointer to zero-terminated string2
;####  r5 is 1 if a match else zero
cmp_str:
mov r5,0x01	; True until found otherwise
cmp_str.start:
mov A,[r0r1]
mov B,A
mov A,[r2r3]
cmp A,B ; test for same character
jnz cmp_str.false ; not same character
cmp A,0x00	; if we got here then A=B 
jz cmp_str.exit ;A=B=0x00
inc r0r1
inc r2r3
jmp cmp_str.start

cmp_str.false:
mov r5,0x00
cmp_str.exit:
pop T
ret

;####  General helper function print_str
;####  r0r1 pointer to null-terminated string
;####  to do: incorporate checking if TX is busy before sending character
print_str:
mov A,[r0r1]
cmp A,0x00 ; test for null-terminated string
jz print_str.end ; change to je for correctness when carry incorporated into logic
push A
print_str.TXWAIT0:
	mov A,F
	and A,0x20
	jnz print_str.TXWAIT0
pop A
mov U,A ; print character
inc r0r1; increment pointer
jmp print_str
print_str.end:
	mov A,F
	and A,0x20
	jnz print_str.end
mov U,0x0A	; newline
print_str.TXWAIT1:
	mov A,F
	and A,0x20
	jnz print_str.TXWAIT1
mov U,0x0D
POP T
RET

;#######################  General helper function print_hex	#######################
;####  Prints the hex of a single byte;						#######################
;####  r4: single byte to print in format 0xYZ				#######################
;####  r5 = 0, don't print leading '0x', else print it  	#######################
;##################################################################################

; Could change this routine to let the user print '0x' or not before calling print_hex
print_hex:
mov A,r5
cmp A,0x00
jz print_hex.nolead

print_hex.TXWAIT0:
	mov A,F
	and A,0x20
	jnz print_hex.TXWAIT0
mov U,0x30	; 48 = '0'

print_hex.TXWAIT1:
	mov A,F
	and A,0x20
	jnz print_hex.TXWAIT1
mov U,0x78	; 120 = 'x'
print_hex.nolead:
mov r5,0x02	; change r5 and use as a loop counter (r5=2)

mov A,r4	
shr A
shr A
shr A
shr A		; shift right A four times to extract upper half

print_hex.process:	; takes 4 LSBs of A and displays hex character
	add A,0x30	; add '0' (48) to A
	cmp A,0x3a	; 0x3a = 58 = position after '9' character
	jl print_hex.digit	; jump if digit is 0-9 and display
	add A,0x07			; map A onto range starting from 65=A otherwise

	print_hex.digit:
		push A
		print_hex.digit.TXWAIT2:
			mov A,F
			and A,0x20
			jnz print_hex.digit.TXWAIT2
		pop A
		mov U,A		; output digit
		dec r5		; changes A
		jz print_hex.exit
		mov A,r4	; restore original r4 byte into A
		and A,0x0F	; Extract lower half
		jmp print_hex.process
	
print_hex.exit:
	POP T
	RET

;####  General helper function cmp_str_special to compare two strings and save the special character # in the zero page
;####  Inputs:
;####  r0r1 pointer to zero-terminated string1 (might contain wild-card character #, which is stored at [r5++])
;####  r2r3 pointer to zero-terminated string2
;####  r5 = zero-page memory address to start putting bytes into. Can't be 0x00 (which is reserved anyway)
;####  Returns:
;####  r5 is non-zero if a match, else zero
;####  Usage:
;####  r0r1 = 'print(##)'
;####  r2r3 = 'print(OK)'
;####  [r5] = 'O', [r5+1]='K'. r5!=0x00 indicates a successful match

cmp_str_special:
	;mov r5,0x01	; True until found otherwise
	push r4
	mov r4,0x88		; ZEROPAGE (will be 0x80 on final hardware)
cmp_str_special.start:
	mov A,[r0r1]
	cmp A,0x23 ; #
	jz cmp_str_special.wildcard
	
	mov B,A
	mov A,[r2r3] 
	cmp A,B ; test for same character
	jnz cmp_str_special.false ; not same character
	cmp A,0x00	; if we got here then A=B 
	jz cmp_str_special.exit ;A=B=0x00
	inc r0r1
	inc r2r3
	jmp cmp_str_special.start
	
cmp_str_special.wildcard:
	mov A,[r2r3]	; get wildcard character from r2r3 string
	mov [r4r5],A;[0x02],A	; put into zero-page address 0x02 (hard coded for now)
	inc r0r1
	inc r2r3
	inc r5			; no memory overflow checking...
	jmp cmp_str_special.start
	
cmp_str_special.false:
	mov r5,0x00
cmp_str_special.exit:
	pop r4	
	pop T
	ret
	
ascii_hex_to_byte:
; ######## ascii_hex_to_byte: General library function ##########################################################
; ######## Notes: No error checking for correct input. Bit crude but should work
; ######## Inputs:
; ######## r4 - address of ascii byte of high nibble, '0-9' char or 'A-F' char 
; ######## r5 - address of ascii byte of low nibble, '0-9' char or 'A-F' char 
; ######## Returns:
; ######## r5 - assembled byte
	mov A,r4
	sub A,0x30 	; 0x30 = 48 = '0'
	mov r4,A	; save result in r4
	and A,0x10	; test 5th bit - overwrites A reg
	mov A,r4	; restore A
	jz ascii_hex_to_byte.r4digit
	sub A,0x07	; 'A' = 65, 65-48-7 = 10 as required.
	ascii_hex_to_byte.r4digit: ; 0-9
	and A,0x0F	; this allows both upper and lower case A-F and a-f
	shl A
	shl A
	shl A
	shl A
	mov r4,A	; high nibble back in r4

	mov A,r5
	sub A,0x30 	; 0x30 = 48 = '0'
	mov r5,A	; save A
	and A,0x10	; test 5th bit
	mov A,r5	; restore A
	jz ascii_hex_to_byte.r5digit
	sub A,0x07	; 0x41 = 65
	ascii_hex_to_byte.r5digit:
	and A,0x0F
	mov B,r4	; high nibble in B
	or A,B		; combine high and low nibble
	mov r5,A	; return byte in r5
	pop T
	ret 
	
;### Programming mode
program_mode:
	mov r2,0x0E	; 0x0E = 14 lines
	mov r0r1, program_mode_str
program_mode.display_text:
	push_pc+1
	call print_str	; Line 1-14
	inc r0r1
	dec r2
	jnz program_mode.display_text

	mov r2r3,input_str ; setup new input string
	mov r4,0x00
	
	program_mode.display_text.TXWAIT:
		mov A,F
		and A,0x20
		jnz program_mode.display_text.TXWAIT
	mov U,0x3E ; ">"

; ################ programming main() ####################
program_mode.loop:
	push_pc+1
	call handle_input	; returns r5=0 if no string, else r5=1
	mov A,r5
	cmp A,0x01
	jz program_mode.loop.process	; we got a match
	jmp program_mode.loop

program_mode.loop.process:
	push_pc+1
	call program_mode.process_str ; process the commands in some way
	mov A,r4			; look at output, if r4!=0 then exit
	cmp A,0x00
	jz program_mode.loop
	; else if we got here, exit program_mode back to main
	pop T
	ret
	
program_mode.process_str:
;	Get address of command string using r4 as an index
	mov r4,0x00 ; command index = 0 initially

program_mode.process_loop:
	mov r2r3, program_cmd_table ; use r2r3 temporarily 
	mov A,r4
	shl A	;A = index * 2
	add A,r3
	mov r3,A
	mov A,r2
	addc A,0x00
	mov r2,A	; r2r3 = program_cmd_table + 2*r4
	
	; need to get address at r2r3 into r0r1:
	mov A,[r2r3]	; HIGH
	mov r0,A
	inc r2r3
	mov A,[r2r3]	; LOW
	mov r1,A
	
	; r0r1 now holds the actual address that was pointed to by r2r3
	
	mov r2r3,input_str	; reset input string pointer
	mov r5,0x02			; set zeropage memory address for wildcard characters
	push_pc+1			
	call cmp_str_special	
	mov A,r5
	cmp A,0x00
	jnz program_mode.success ; r5 !=0  means command recognised

	mov A,r4	; loop counter
	inc A
	mov r4,A

	cmp A,0x0D ; 13 commands
	jnz program_mode.process_loop
	; if we got here then went through all strings and didn't match
	mov r0r1,error_str
	push_pc+1
	call print_str
	jmp program_mode.reset_prompt

program_mode.jump_table:
dw program_mode.set_high,program_mode.set_highHEX, program_mode.set_low,program_mode.set_lowHEX, program_mode.addr
dw program_mode.readbyte,program_mode.writebyte,program_mode.writebyteHEX,program_mode.inc,program_mode.dec
dw program_mode.jump,program_mode.eoc,program_mode.leave 

program_mode.success:	; Use r4 as an index for a jump table
	mov r0r1,program_mode.jump_table
	mov A,r4 ; index into jump table
	shl A
	add A,r1 ; add r0r1+A --> A is jump table index
	mov r1,A
	mov A,r0
	addc A,0x00
	mov r0,A 	; r0r1 is now the pointer to the desired jump label

	mov A,[r0r1]	; HIGH byte of desired jump label
	push A
	inc r0r1
	mov A,[r0r1]	; LOW byte of desired jump label
	push A
	pop PC ; jmp!
	
; current address is at zero page, 0x03 (hi) and 0x04 (low)
program_mode.set_high:
	mov A,[0x02]
	mov [0x0A],A
	jmp program_mode.reset_prompt
	
program_mode.set_highHEX:
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov [0x0A],r5
	jmp program_mode.reset_prompt

program_mode.set_low:
	mov A,[0x02]
	mov [0x0B],A
	jmp program_mode.reset_prompt

program_mode.set_lowHEX:
	mov r4,[0x02]	; high hex nibble in ascii 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov [0x0B],r5
	jmp program_mode.reset_prompt
	
program_mode.addr:
	mov r5,0x01	; print 0x in print_hex
	mov r4,[0x0A]	; Display interrupt vector address
	push_pc+1
	call print_hex
	mov r5,0x00	; don't print 0x in print_hex
	mov r4,[0x0B]	; Display interrupt vector address
	push_pc+1
	call print_hex
	jmp program_mode.reset_prompt
program_mode.readbyte:
	mov r0,[0x0A]
	mov r1,[0x0B]
	mov A,[r0r1]
	mov r5,0x01
	mov r4,A
	push_pc+1
	call print_hex
	jmp program_mode.reset_prompt
program_mode.writebyte:
	mov r0,[0x0A]
	mov r1,[0x0B]
	mov A,[0x02]
	mov [r0r1],A
	jmp program_mode.reset_prompt
program_mode.writebyteHEX:
	mov r4,[0x02]	; high hex nibble in ascii, 0-9 and A-F (caps)
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov A,r5	; assembled byte 
	mov r0,[0x0A]
	mov r1,[0x0B]
	mov [r0r1],A	; write r5 into addressed specified in 0x0A-0x0B
	jmp program_mode.reset_prompt
program_mode.inc:
	mov r0,[0x0A]
	mov r1,[0x0B]
	inc r0r1
	mov [0x0A],r0
	mov [0x0B],r1
	jmp program_mode.reset_prompt
program_mode.dec:
	mov A,[0x0B]
	dec A
	mov [0x0B],A
	mov A,[0x0A]
	subc A,0x00
	mov [0x0A],A
	jmp program_mode.reset_prompt
program_mode.jump:
	mov A,[0x0A]	; HIGH byte of desired jump label
	push A
	inc r0r1
	mov A,[0x0B]	; LOW byte of desired jump label
	push A
	pop PC ; jmp!
	jmp program_mode.reset_prompt
program_mode.eoc:
	mov r0r1,END_OF_CODE
	mov r5,0x01	; print 0x in print_hex
	mov r4,r0	; Display interrupt vector address
	push_pc+1
	call print_hex
	mov r5,0x00	; don't print 0x in print_hex
	mov r4,r1	; Display interrupt vector address
	push_pc+1
	call print_hex
	jmp program_mode.reset_prompt
program_mode.leave:
	mov r4,0xff	; use r4 as a return register, signals to exit to main
	pop T
	ret
	
program_mode.reset_prompt:
	mov r2r3,input_str ; setup new input string
	mov r4,0x00
	
	program_mode.reset_prompt.TXWAIT:
		mov A,F
		and A,0x20
		jnz program_mode.reset_prompt.TXWAIT
	mov U,0x3E ; ">"
	pop T
	ret
	
;Zero page structure:
; 0x00-0x01 RESERVED INT VECTOR
; 0x02-0x09 8 bytes for special str cmp
; 0x0A-0x0B programming current address (0x0A = High, 0x0B = Low byte)

; data labels don't have to be page-aligned
welcome: dstr 'Welcome to Duncatron v1.0'
ready: dstr 'READY'
helloworld: dstr 'Hello world @=)'
interupt_text: dstr 'Interupt called!'
exit_str: dstr 'exit'
goodbye_str: dstr 'Bye!'
error_str: dstr 'ERROR'
program_str: dstr 'prog'
program_mode_str: ; Humans can input bytes using hex 0x##, computers by sending byte directly ie: #
dstr 'Entering PROGRAMMING mode. Commands:' ; this comment gets ignored
dstr '			h#  	; set high address to # (#=byte)'
dstr '			h 0x##  ; set high address to 0x## (#=byte)'
dstr '			l#  	; set low address to #'
dstr '			l 0x##  ; set low address to 0x##'
dstr '			a		; display current address'
dstr '			r   	; read the byte at current address'
dstr '			w#  	; write the byte # at current address'
dstr '			w 0x##  ; write the byte 0x## at current address'
dstr '			+   	; increment address +1'
dstr '			-   	; decrement address -1'
dstr '			j   	; jump to current address'
dstr '			eoc		; display end of code address'
dstr '			x		; leave programming mode'

program_cmd_table:
dw cmd0,cmd1,cmd2,cmd3,cmd4,cmd5,cmd6,cmd7,cmd8,cmd9,cmdA,cmdB,cmdC
cmd0: dstr 'h#'
cmd1: dstr 'h 0x##'
cmd2: dstr 'l#'
cmd3: dstr 'l 0x##'
cmd4: dstr 'a'
cmd5: dstr 'r'
cmd6: dstr 'w#'
cmd7: dstr 'w 0x##'
cmd8: dstr '+'
cmd9: dstr '-'
cmdA: dstr 'j'
cmdB: dstr 'eoc'
cmdC: dstr 'x'
jumpstring:
dstr 'Jumped!'
;dstr 'h#|l#|r|w#|i||d|j
input_str: db [129]; Need to have some kind of array notation for making fixed sizes, i.e. db [129]
END_OF_CODE: ; Label useful so we know where we can safely start programming

;0x4161: ;0x41 =A, 0x61 =a
;	mov r0r1,jumpstring
;	push_pc+1
;	call print_str
;	jmp program_mode.reset_prompt

; can have a command, i.e. "eoc" that produces:
; > eoc
; print_eoc:
; mov r0r1,END_OF_CODE
; mov r5,0x01	; print 0x in print_hex
; mov r4,r0	; Display interrupt vector address
; push_pc+1
; call print_hex
; mov r5,0x00	; don't print 0x in print_hex
; mov r4,r1	; Display interrupt vector address
; push_pc+1
; call print_hex

; Consider adding some support for constants, can use as variables in 16-bit memory and 8-bit zero-page addresses.
; (1) Add assignment and typing by 8 or 16-bit
; (2) Add regex for zeropage addressing and using labels rather than 0x@@ constants
; i.e.:
; ZEROPAGE 		= 0x8000 ; for example
; constant16	= 0x1234
; RESERVED 		= 0x00 	; for interrupt vector
; loop_index 	= 0x02 ; one byte
; my_var1 		= 0x03 ; two bytes
; my_var2		= 0x05 ; two bytes
; test0			= 0x07 ; one byte

; then can have:
; mov A, [loop_index]
; inc A
; mov [loop_index],A
; 
; or:
; mov r0r1,constant16
; jmp ZEROPAGE

