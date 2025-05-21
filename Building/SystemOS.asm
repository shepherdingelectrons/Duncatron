init:
	mov r0r1,INTERUPT; setup interrupt jump vector
	mov [0x00],r0	; Zero page 0x00
	mov [0x01],r1	; Zero page 0x01

	push_pc+1
	call draw_logo
	
	mov r0r1,welcome	; Print a greeting message
	push_pc+1
	call print_str
	
	mov r0r1,ready	; READY
	push_pc+1
	call print_str

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
	jnz main_loop
	; If r5==1 then an input is available
	push_pc+1
	call execute_cmd ; Try and execute command
	mov A,r4	; check return code
	cmp A,0xff	; if r4==0xff then means a special case where running main.exit
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

draw_logo:

	mov r0r1,duncatron1_0	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron1_1	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron1_2	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron1_3	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron1_4	; Print a greeting message
	push_pc+1
	call print_str
	
	pop T
	RET
	
draw_logo_2:
	mov r0r1,duncatron0	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron1	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron2	; Print a greeting message
	push_pc+1
	call print_str
	mov r0r1,duncatron3	; Print a greeting message
	push_pc+1
	call print_str
	
	pop T
	RET

COMMAND_TABLE_LEN equ 0x08

main_commands_table:
dw exit_str, prog_str, write_byte_str, read_byte_str
dw hex_str, logo_str, logo_str2, help_str

main_commands_jumptable:
dw execute_cmd.run_exit, execute_cmd.prog, execute_cmd.write_byte, execute_cmd.read_byte
dw execute_cmd.hex, execute_cmd.draw_logo, execute_cmd.draw_logo_2, execute_cmd.help

exit_str: dstr 'exit'
prog_str: dstr 'prog'
write_byte_str: dstr 'w 0x#### 0x##'
read_byte_str: dstr 'r 0x####'
hex_str: dstr 'hex 0x#### 0x##'
logo_str: dstr 'logo'
logo_str2: dstr 'logo2'
help_str: dstr 'help'

execute_cmd:
	mov r2r3,main_commands_table ; pointer to command table, contains list of pointers
	mov r4,0x00	; command counter
	
execute_cmd.checkcmds_loop:
	; need to get address at r2r3 into r0r1:
	mov A,[r2r3]	; HIGH
	mov r0,A
	inc r2r3
	mov A,[r2r3]	; LOW
	mov r1,A
	
	; r0r1 now holds the specific command string address
	push r2
	push r3
	mov r2r3,input_str
	mov r5,0x02	; position in zeropage to put special wild card characters
	push_pc+1
	call cmp_str_special
	mov A,r5
	cmp A,0x00 ; if r5!=0 then command recognised, r4 holds array position
	pop r3
	pop r2
	
	jnz execute_cmd.success
	
	inc r2r3

	inc r4	; Next pointer position
	mov A,r4	; instruction not needed?

	cmp A,COMMAND_TABLE_LEN ; finished all main commands?
	jnz execute_cmd.checkcmds_loop
	; If we got here then we didn't find any matches...

execute_cmd.error:
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

execute_cmd.success: ; use r4 as an index for a jump table
	mov r0r1,main_commands_jumptable
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

execute_cmd.run_exit: ; 'exit' command found
	mov r4,0xff		; r4=0xFF is the return code that is checked for to signify exit condition
	pop T
	ret

execute_cmd.prog:
	push_pc+1
	call program_mode
	; would return here from program_mode if called
	mov r0r1,ready	; Print a greeting message
	push_pc+1
	call print_str
	
	jmp execute_cmd.exit

execute_cmd.write_byte:
	; Convert string to 16-bit hex address, convert write-byte string to 8-bit value
	; Write write-byte to 16-hex address (be careful of register usage in conversion functions)
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r0,r5
	
	mov r4,[0x04]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x05]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r1,r5
	
	; we now have the 16-bit address in r0r1
	mov r4,[0x06]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x07]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov A,r5
	mov [r0r1],A
	mov U,'O'
	mov U,'K'
	mov U,0x0A
	mov U,0x0D
	
	jmp execute_cmd.exit
	
execute_cmd.read_byte:
	; Convert string to 16-bit hex address, read byte and display as hex
	; (be careful of register usage in conversion functions)
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r0,r5
	
	mov r4,[0x04]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x05]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r1,r5
	
	; we now have the 16-bit address in r0r1
	mov r5,0x01	; print 0x in print_hex
	mov A,[r0r1]
	mov r4,A
	push_pc+1
	call print_hex
	mov U,0x0A
	mov U,0x0D
	
	jmp execute_cmd.exit

execute_cmd.hex:
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r0,r5		; HIGH of start address
	
	mov r4,[0x04]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x05]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r1,r5		; LOW of start address
	
	mov r4,[0x06]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x07]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r3,r5		; number of bytes to display
	mov r2,0x00		; r2 is counter
	
	hex.newline:
	mov A,r2
	cmp A,r3
	je hex.leave	; check if we have read specified number of bytes yet
	
	mov U,0x0A
	mov U,0x0D
	
	mov r5,0x01		; Display 16-bit address
	mov r4,r0
	push_pc+1
	call print_hex
	mov r4,r1
	
	mov r5,0x00
	push_pc+1
	call print_hex
	
	mov U,':'
	mov U,' '
	
	hex.loop:
		mov A,[r0r1]	; byte to print (r5!=0, display '0x', r5=0, don't display 0x)
		mov r4,A
		mov r5,0x00
		push_pc+1
		call print_hex
		mov U,' '
		
		inc r0r1	; next position in memory
		inc r2
		mov A,r2
		dec A
		and A,0x0f	; A will contain r2
		cmp A,0x0f
		je hex.endline	; if counter is a multiple of 16 do a new line
		
		mov A,r2
		cmp A,r3
		jne hex.loop	; check if we have read specified number of bytes yet - if not, re-loop
	
	hex.endline:
	; do some end line stuff
	mov r4,r0
	mov r5,r1 ; copy r0r1 pointer
	
	mov A,r5
	sub A,0x10
	mov r5,A
	mov A,r4
	subc A,0x00
	mov r4,A
	
	mov A,0x00
	hex.endline_loop:
		mov [0x02],A
		mov A,[r4r5]
		cmp A,0x20	; 32 
		jge endline_loop_display ; 0x7F = 127 = backspace might mess this up in Putty
		mov A,0x2E ; '.'
		
		endline_loop_display:
		mov U,A
	
		inc r4r5
		mov A,[0x02]
		inc A
		cmp A,0x10
		jne hex.endline_loop
	
	mov A,r2
	cmp A,r3
	jne hex.newline	; check if we have read specified number of bytes yet
	
	hex.leave:	
	mov U,0x0A
	mov U,0x0D
	jmp execute_cmd.exit

execute_cmd.draw_logo:
	push_pc+1
	call draw_logo
	jmp execute_cmd.exit
	
execute_cmd.draw_logo_2:
	push_pc+1
	call draw_logo_2	
	jmp execute_cmd.exit
	
execute_cmd.help:
	mov r4,COMMAND_TABLE_LEN
	mov r2r3,main_commands_table
	help.printloop:
		
		; need to get address at r2r3 into r0r1:
		mov A,[r2r3]	; HIGH
		mov r0,A
		inc r2r3
		mov A,[r2r3]	; LOW
		mov r1,A
		
		push_pc+1
		call print_str
		
		inc r2r3
		dec r4
		mov A,r4	; A may already contain r4 from above?
		cmp A,0x00
		jnz help.printloop
		
	jmp execute_cmd.exit
	
execute_cmd.next3:
; ... other programs here
	jmp execute_cmd.exit


; ########### Interupt vector ##################
INTERUPT:
mov r0r1,interupt_text
push_pc+1
call print_str
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
cmp A,0x0D ; Alternative return = 13 = 0x0D
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
mov [r2r3],A ; Write character to memory
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
	mov r4,0x80		; ZEROPAGE (will be 0x80 on final hardware)
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
	cmp A,0x00		; catch the case that the matched character is actually the end of string...
	jz cmp_str_special.false	; # != 0x00 so raise mismatch case
	
	mov [r4r5],A; put into zero-page address 0x80:r5
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
	mov U,0x3F; ":" ;0x3E ; ">"

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
	
; old code below, set_high, writebyte, set_low

program_mode.set_high:
	mov A,[0x02]
	mov [0x0A],A
	jmp program_mode.reset_prompt
	
program_mode.set_low:
	mov A,[0x02]
	mov [0x0B],A
	jmp program_mode.reset_prompt
	
program_mode.writebyte:
	mov r0,[0x0A]
	mov r1,[0x0B]
	mov A,[0x02]
	mov [r0r1],A
	jmp program_mode.reset_prompt

; current address is at zero page 0x03 (hi) and 0x04 (low)
program_mode.set_n:	;sets number of bytes for serial read and write operations
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov [0x0C],r5	; store number of bytes in 0x0C on zeropage
	jmp program_mode.reset_prompt
	
program_mode.writestream:
	; we now setup a loop which waits for n+1 characters on the UART RX stream
	; we echo each one back so that the sending knows we have received and okay to send another
	mov r5,[0x0C]	; number pf bytes (0-255)--> 1-256 bytes
	mov r0,[0x0A]	; high byte of address
	mov r1,[0x0B]	; low byte of address

; Consider adding, auto address incrementing and read command as: r 0x##
program_mode.writestream.loop:
		mov A,F	;128 64 32 16 8  4   2  1
				;F7  F6 SD RDY OF N  C  Z
		and A,0x10 ; RX character is waiting
		jz program_mode.writestream.loop
		
		mov A,U		; get RX character from UART
		mov U,A		; send back (assume not sending, don't check for now...)
		
		; Do something with the character, write it somewhere I guess
		mov [r0r1],A
		
		mov A,r5	; check loop counter
		cmp A,0x00
		jz program_mode.reset_promptNL ; if zero, A-0 = 0, then bail out
		
		dec r5	; by doing decrement after compare, 0 is mapped to 1 byte and 255 is mapped to 256 bytes
		inc r0r1
		
		jmp program_mode.writestream.loop

program_mode.readstream:
	mov r5,[0x0C]	; number pf bytes (0-255)--> 1-256 bytes
	mov r0,[0x0A]	; high byte of address
	mov r1,[0x0B]	; low byte of address
		
program_mode.readstream.loop:
	mov A,F	;128 64 32 16 8  4   2  1
				;F7  F6 SD RDY OF N  C  Z
	and A,0x20 ; TX character is still sending, wait...
	jnz program_mode.readstream.loop
	
	mov A,[r0r1]
	mov U,A		; send char at memory address
	
	mov A,r5	; check loop counter
	cmp A,0x00
	jz program_mode.reset_promptNL ; if zero, A-0 = 0, then bail out
		
	dec r5	; by doing decrement after compare, 0 is mapped to 1 byte and 255 is mapped to 256 bytes
	inc r0r1
	
	jmp program_mode.readstream.loop

program_mode.set_highHEX:
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov [0x0A],r5
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
	jmp program_mode.reset_promptNL

program_mode.readbyte:
	mov r0,[0x0A]
	mov r1,[0x0B]
	mov A,[r0r1]
	mov r5,0x01
	mov r4,A
	push_pc+1
	call print_hex
	jmp program_mode.reset_promptNL

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
	jmp program_mode.reset_promptNL

program_mode.leave:
	mov r4,0xff	; use r4 as a return register, signals to exit to main
	pop T
	ret

program_mode.reset_promptNL:
	mov U,0x0A	; newline
	mov U,0x0D	; carriage-return

program_mode.reset_prompt:
	mov r2r3,input_str ; setup new input string

	mov r4,0x00	
	mov U,0x3F; ":" ;0x3E ; ">"
	pop T
	ret

program_mode.jump_table:
dw program_mode.set_highHEX, program_mode.set_lowHEX, program_mode.addr
dw program_mode.readbyte,program_mode.writebyteHEX,program_mode.inc,program_mode.dec
dw program_mode.jump,program_mode.set_n,program_mode.writestream,program_mode.readstream
dw program_mode.eoc,program_mode.leave 

;Zero page structure:
; 0x00-0x01 RESERVED INT VECTOR
; 0x02-0x09 8 bytes for special str cmp
; 0x0A-0x0B programming current address (0x0A = High, 0x0B = Low byte)
; 0x0C		number of bytes for serial writing and reading

; data labels don't have to be page-aligned
welcome: dstr 'Welcome to Duncatron v1.0 - type "help" for commands'
ready: dstr 'READY'
helloworld: dstr 'Hello world @=)'
interupt_text: dstr 'Interupt called!'
goodbye_str: dstr 'Bye!'
error_str: dstr 'ERROR'

program_mode_str: ; Humans can input bytes using hex 0x##, computers by sending byte directly ie: #
dstr 'Entering PROGRAMMING mode. Commands:' ; this comment gets ignored
dstr '			h 0x##	; set high address to 0x## (#=byte)'
dstr '			l 0x##	; set low address to 0x##'
dstr '			a		; display current address'
dstr '			r		; read the byte at current address'
dstr '			w 0x##	; write the byte 0x## at current address'
dstr '			+		; increment address +1'
dstr '			-		; decrement address -1'
dstr '			j		; jump to current address'
dstr '			n 0x##	; set num bytes (0-255) for serial w/r'
dstr '			ws		; write serial stream (writes n+1) bytes'
dstr '			rs		; read serial stream (reads n+1) bytes'
dstr '			eoc		; display end of code address'
dstr '			x		; leave programming mode'

; old strings:
dstr '			h#  	; set high address to # (#=byte)'
dstr '			l#		; set low address to # (#=byte)'
dstr '			w#  	; write the byte # at current address'

; Logo generated here: https://patorjk.com/software/taag/#p=testall&f=Bulbhead&t=Duncatron%20
duncatron0: dstr ' ____  __  __  _  _  ___    __   ____  ____  _____  _  _'  
duncatron1: dstr '(  _ \(  )(  )( \( )/ __)  /__\ (_  _)(  _ \(  _  )( \( )'
duncatron2: dstr ' )(_) ))(__)(  )  (( (__  /(__)\  )(   )   / )(_)(  )  ('
duncatron3: dstr '(____/(______)(_)\_)\___)(__)(__)(__) (_)\_)(_____)(_)\_)' 

duncatron1_0: dstr '    ____                         __'                 
duncatron1_1: dstr '   / __ \__  ______  _________ _/ /__________  ____'     
duncatron1_2: dstr '  / / / / / / / __ \/ ___/ __ `/ __/ ___/ __ \/ __ \'     
duncatron1_3: dstr ' / /_/ / /_/ / / / / /__/ /_/ / /_/ /  / /_/ / / / /'     
duncatron1_4: dstr '/_____/\__,_/_/ /_/\___/\__,_/\__/_/   \____/_/ /_/' 

; Tidy up commands, remove h# and l#
; Tidy up EOL (13,10 = 0x0D,0x0A) behaviour to make automated access easier
; add 'ws 0x##' and 'rs 0x##' = write serial and read serial, 
; where '0x##' is the number of characters to write/read in a following serial stream

program_cmd_table:
dw cmd0,cmd1,cmd2,cmd3,cmd4,cmd5,cmd6,cmd7,cmd8,cmd9,cmdA,cmdB,cmdC
cmd0: dstr 'h 0x##'
cmd1: dstr 'l 0x##'
cmd2: dstr 'a'
cmd3: dstr 'r'
cmd4: dstr 'w 0x##'
cmd5: dstr '+'
cmd6: dstr '-'
cmd7: dstr 'j'
cmd8: dstr 'n 0x##'
cmd9: dstr 'ws'
cmdA: dstr 'rs'
cmdB: dstr 'eoc'
cmdC: dstr 'x'
jumpstring:
dstr 'Jumped!'
;dstr 'h#|l#|r|w#|i||d|j
END_OF_CODE: ; Label useful so we know where we can safely start programming
push_pc+1
int
mov U,0x40 ; '@'
halt

0x8200:
input_str: db [129]; Need to have some kind of array notation for making fixed sizes, i.e. db [129]

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

