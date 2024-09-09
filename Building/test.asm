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

;### Programming mode
;### Will be useful to have a HEX byte print function
program_mode:
mov r2,0x0A	; 10 lines
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

; ################ main() ####################
program_mode.loop:
	push_pc+1
	call handle_input	; returns r5=0 if no string, else r5=1
	mov A,r5
	cmp A,0x01
	;push_pc+1
	;call_z execute_cmd ; process the commands in some way

	jmp program_mode.loop

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
dstr 'Entering PROGRAMMING mode' ; this comment gets ignored
dstr 'Commands:	h#  ; set high address to # (#=byte)'
dstr '			l#  ; set low address to #'
dstr '			a## ; set 16-bit address to ##'
dstr '			i   ; increment address +1'
dstr '			d   ; decrement address -1'
dstr '			w#  ; write the byte @ at current address'
dstr '			r   ; read the byte at current address'
dstr '			j   ; jump to current address'
dstr '			u   ; uart serial mode (no carriage return)'
input_str: ;
