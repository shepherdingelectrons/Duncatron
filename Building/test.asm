mov r0r1,jump_table
mov A,0x02 ; index into jump table
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
pop PC ; jmp init!

mov U,0x43 ; C

db 0x06,0x09,0x0A,69,42
dw 0x1234,0x6942,258

jump_table:
dw wrong,wrong,init,wrong,wrong,0x4321,513,input_str

wrong:
mov U,0x44 ;D

init:
mov U,0x45 ;E
mov r0r1,INTERUPT; setup interrupt jump vector
mov [0x00],r0	; Zero page 0x00
mov [0x01],r1	; Zero page 0x01

mov r5,0x01	; print 0x in print_hex
mov r4,r0	; Display interrupt vector address
push_pc+1
call print_hex
mov r5,0x00	; no leading 0x
mov r4,r1
push_pc+1
call print_hex

mov r0r1,ready	; Print a greeting message
push_pc+1
call print_str

mov A,0x50 ; P
mov U,A
shr A
mov U,A    ; 0x28 = (

; New string:
mov r2r3,input_str
mov r4,0x00
mov U,0x3E ; ">"
mov A,U ; clear uart register

; ################ main() ####################
main_loop:
push_pc+1
call handle_input	; returns r5=0 if no string, else r5=1
mov A,r5
cmp A,0x01
push_pc+1
call_z execute_cmd

jmp main_loop

main.exit:
mov r0r1,goodbye_str
push_pc+1
call print_str
HALT
jmp init ; If restart after HALT without reseting PC

; ################  Execute commands if matched #########
execute_cmd:
mov r0r1,exit_str
mov r2r3,input_str 
push_pc+1
call cmp_str
mov A,r5
cmp A,0x01
jz main.exit	; exit main loop and HALT

mov r0r1,program_str
mov r2r3,input_str 
push_pc+1
call cmp_str
mov A,r5
cmp A,0x01
push_pc+1
call_z program_mode
jmp execute_cmd.exit

; Else, command not found
; Throw an error
mov r0r1,error_str
push_pc+1
call print_str

execute_cmd.exit:
mov r2r3,input_str ; setup new input string
mov r4,0x00
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
mov U,A ; send character it back!
mov [r2r3],A
inc r2r3
inc r4 
jmp handle_input.exit

handle_input.backchar:
mov A,r4
cmp A,0x00 ; compare r4 to 0, if jz don't delete char else delete char
jz handle_input.exit
mov U,0x7F ; Send backspace to console
dec r4 
dec r3 ; decrease r2r3  pointer
mov A,r2
subc A,0x00
mov r2,A
jmp handle_input.exit

handle_input.endstr:
mov U,0x0A
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
mov U,A ; print character
inc r0r1; increment pointer
jmp print_str
print_str.end:
mov U,0x0A	; newline
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

mov U,0x30	; 48 = '0'
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
		mov U,A		; output digit
		dec r5		; changes A
		jz print_hex.exit
		mov A,r4	; restore original r4 byte into A
		and A,0x0F	; Extract lower half
		jmp print_hex.process
	
print_hex.exit:
	POP T
	RET
;####  General helper function to compare two strings and save the special character # in the zero page
;####  r0r1 pointer to zero-terminated string1 (might contain wild-card character #, could pass on as r4?)
;####  r2r3 pointer to zero-terminated string2
;####  r5 is 1 if a match else zero
;####  Usage:
;####  r0r1 = 'print(#)'
;####  r2r3 = 'print(A)'
;####  zero page address (0x02) would contain 'A' and r5=1 would indicate a successful match

cmp_str_special:
	mov r5,0x01	; True until found otherwise
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
	mov [0x02],A	; put into zero-page address 0x02 (hard coded for now)
	inc r0r1
	inc r2r3
	jmp cmp_str_special.start
	
cmp_str_special.false:
	mov r5,0x00
cmp_str_special.exit:
	pop T
	ret
	
;### Programming mode
program_mode:
mov r2,0x01	; 10 lines
mov r0r1, program_mode_str
program_mode.display_text:
	push_pc+1
	call print_str	; Line 1-10
	inc r0r1
	dec r2
	jnz program_mode.display_text

mov r2r3,input_str ; setup new input string
mov r4,0x00
mov U,0x3E ; ">"

; ################ programming main() ####################
program_mode.loop:
	push_pc+1
	call handle_input	; returns r5=0 if no string, else r5=1
	mov A,r5
	cmp A,0x01
	push_pc+1
	call_z program_mode.process_str ; process the commands in some way
	jmp program_mode.loop

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
	push_pc+1			
	call cmp_str_special	
	mov A,r5
	cmp A,0x00
	jnz program_mode.success ; r5 = 1 means command recognised

	mov A,r4	; loop counter
	inc A
	mov r4,A
	add A,0x61	; 0x61 = 'a'
	mov U,A
	
	mov A,r4
	cmp A,0x09
	jnz program_mode.process_loop
	; if we got here then went through all strings and didn't match
	mov r0r1,error_str
	push_pc+1
	call print_str
	jmp program_mode.reset_prompt
	
program_mode.success:	; Use r4 as an index for a jump table
	mov A,0x41 ; 0x41 = 'A'
	add A,r4; 0x41 ; add 'A' to command index r4
	mov U,A	
	mov A,[0x02] ; display last wild card in the zero page
	mov U,A
	;jmp program_mode.reset_prompt

program_mode.reset_prompt:
	mov r2r3,input_str ; setup new input string
	mov r4,0x00
	mov U,0x3E ; ">"
	pop T
	ret

program_mode.jump_table:
dw program_mode.set_high,program_mode.set_low,program_mode.readbyte,program_mode.writebyte
dw program_mode.inc,program_mode.dec,program_mode.jump ; for readability

program_mode.set_high:
	nop
program_mode.set_low:
	nop
program_mode.readbyte:
	nop
program_mode.writebyte:
	nop
program_mode.inc:
	nop
program_mode.dec:
	nop
program_mode.jump:
	nop
	
; data labels don't have to be page-aligned
welcome: dstr 'Welcome to Duncatron v1.0'
ready: dstr 'READY'
helloworld: dstr 'Hello world @=)'
interupt_text: dstr 'Interupt called!'
exit_str: dstr 'exit'
goodbye_str: dstr 'Bye!'
error_str: dstr 'ERROR'
program_str: dstr 'prog'
program_mode_str:
dstr 'Entering PROGRAMMING mode. Commands:' ; this comment gets ignored
dstr '			h#  ; set high address to # (#=byte)'
dstr '			l#  ; set low address to #'
dstr '			a	; display current address'
dstr '			r   ; read the byte at current address'
dstr '			w#  ; write the byte @ at current address'
dstr '			i   ; increment address +1'
dstr '			d   ; decrement address -1'
dstr '			j   ; jump to current address'
dstr '			eoc	; display end of code address'
;program_commands:	
program_cmd_table:
dw cmd0,cmd1,cmd2,cmd3,cmd4,cmd5,cmd6,cmd7,cmd8
cmd0: dstr 'h#'
cmd1: dstr 'l#'
cmd2: dstr 'a'
cmd3: dstr 'r'
cmd4: dstr 'w#'
cmd5: dstr 'i'
cmd6: dstr 'd'
cmd7: dstr 'j'
cmd8: dstr 'eoc'

;dstr 'h#|l#|r|w#|i||d|j
input_str: db [129]; Need to have some kind of array notation for making fixed sizes, i.e. db [129]
END_OF_CODE: ; Label useful so we know where we can safely start programming
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

