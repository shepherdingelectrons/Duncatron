; ******************************* Duncatron BIOS **************************************
init:
NES_PORT equ 0x8100
SOUND_PORT equ 0x8101
COMMAND_TABLE_LEN equ [0x0D]

	mov r0r1,INTERUPT; setup interrupt jump vector
	mov [0x00],r0	; Zero page 0x00
	mov [0x01],r1	; Zero page 0x01

	mov A,0x09		; COMMAND_TABLE_LEN
	mov COMMAND_TABLE_LEN,A	; reset COMMAND_TABLE_LEN
	
	mov U,0x0A
	mov U,0x0D

	push_pc+1
	call sound_off
	
	push_pc+1
	call tune
	
	push_pc+1
	call draw_logo
	
	mov r0r1,welcome	; Print a greeting message
	push_pc+1
	call print_str
	
	mov A,[NES_PORT]	; Checks if NES controller is connected
	cmp A,0x00
	jz no_nes
	
	mov r0r1,NES_found
	push_pc+1
	call print_str

no_nes:
	mov r0r1,ready	; READY
	push_pc+1
	call print_str
	
	push_pc+1
	call tune

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
	je main.exit
	cmp A,0xfe
	je init
	
	jmp main_loop

main.exit:
	mov r0r1,goodbye_str
	push_pc+1
	call print_str
	HALT
	jmp init ; If restart after HALT without reseting PC
		
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

sound_off:
	mov A,0x9F
	mov [SOUND_PORT],A
	mov A,0xBF
	mov [SOUND_PORT],A
	mov A,0xDF
	mov [SOUND_PORT],A
	mov A,0xFF
	mov [SOUND_PORT],A
	pop T
	ret
	
tune:
	mov r0r1,0x015d
	push_pc+1
	call playbeep
	
	mov r0r1,0x00ae
	push_pc+1
	call playbeep
	
	mov r0r1,0x0057
	push_pc+1
	call playbeep
	
	mov r0r1,0x002e
	push_pc+1
	call playbeep
	
	push_pc+1
	call sound_off
	
	pop T
	RET
	
playbeep:
	; r0r1 contains 10-bit number
	
	; First byte: 0b1-ch1-ch0-0-f3-f2-f1-f0
	; Second byte:0b0- x -f9-f8-f7-f6-f5-f4
	mov A,r1
	and A,0x0F
	or A,0x80	; channel 0
	mov [SOUND_PORT],A
	
	
	mov A,r0	; 0b0-0-0-0-0-0-f9-f8
	shl A
	shl A
	shl A
	shl A 		; 0b0-0-f9-f8-0-0-0-0
	mov B,A		; store in B
	mov A,r1	; 0bf7-f6-f5-f4-f3-f2-f1-f0
	shr A
	shr A
	shr A
	shr A		; 0b0000f7-f6-f5-f4
	or A,B	
	mov [SOUND_PORT],A
	
	mov A,0x90			; Attenuation byte, channel 0 
	mov [SOUND_PORT],A

	pop T
	ret

; ###########################  Execute commands if matched #########################################
; ##############  r4 returns 0xff (non-zero) to exit main(), else r4 = 0 (doing nothing for now)  ##

COMMAND_TABLE_LEN_MAX equ 0x10

main_commands_table:
dw hex_str, write_byte_str, read_byte_str, call_str
dw load_str, beep_str, add_cmd_str, reset_str
dw help_str, slot0_str, slot1_str, slot2_str ; add empty slots
dw slot3_str, slot4_str, slot5_str, slot6_str ; add empty slots

; might be fun to add a command to add new command
; addcmd 0x#### *		; * is new nomenclature to be implemented that puts remainder of string into buffer (or saves position of * without further processing)
; i.e. "addcmd 0x8300 beep 0x##"
; "addcmd 0x8400 spitest"
; "addcmd 0x8500 print *"
; "addcmd loadpage 0x8### 0x##" ; load a program into RAM at 0x8###, 0x## number of bytes
; don't forget to increment COMMAND_TABLE_LEN (copy as a variable and put into RAM in init)
; will be useful to load new functions into RAM memory and then add as commands
 
main_commands_jumptable:
dw execute_cmd.hex, execute_cmd.write_byte, execute_cmd.read_byte, execute_cmd.call
dw execute_cmd.load, execute_cmd.beep, execute_cmd.add_cmd, execute_cmd.run_reset
dw execute_cmd.help,0x0000, 0x0000,0x0000 ; add empty slots
dw 0x0000,0x0000,0x0000,0x0000 ; add empty slots

hex_str: dstr 'hex 0x#### 0x##'
write_byte_str: dstr 'w 0x#### 0x##'
read_byte_str: dstr 'r 0x####'
call_str: dstr 'call 0x####'
load_str: dstr 'load 0x####'
beep_str: dstr 'beep 0x####'
add_cmd_str: dstr 'addcmd 0x#### *'	; * is a wildcard that saves the rest of the string
reset_str: dstr 'reset'
help_str: dstr 'help'
slot0_str: db [17] ; 16 characters + 1 zero
slot1_str: db [17] ; 16 characters + 1 zero
slot2_str: db [17] ; 16 characters + 1 zero
slot3_str: db [17] ; 16 characters + 1 zero
slot4_str: db [17] ; 16 characters + 1 zero
slot5_str: db [17] ; 16 characters + 1 zero
slot6_str: db [17] ; 16 characters + 1 zero

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
	
	mov B,COMMAND_TABLE_LEN
	cmp A,B ; finished all main commands?
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
	mov r4,A
	inc r0r1
	mov A,[r0r1]	; LOW byte of desired jump label
	mov r5,A
	
	mov A,r4
	and A,0x80		; is address in RAM?
	jz success.jmp
	; Not in RAM, so a BIOS ROM function - not perfect assumption but does for now
	
	push_pc+1	; if a CALL then push return address
	
	success.jmp:
	push r4
	push r5
	pop PC ; jmp/call!
	jmp execute_cmd.exit ; CALLs will return here so take care of its

execute_cmd.run_reset: ; 'reset' command found
	mov r4,0xfe		; r4=0xFE is the return code for reset
	pop T
	ret

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
	inc r3
	mov r2,0x00		; r2 is counter
	
	hex.newline:
	;mov A,r2
	;cmp A,r3
	;je hex.leave	; check if we have read specified number of bytes yet
	
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

execute_cmd.call:
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
	
	push_pc+1	; push return address (3 bytes from here)
	push r0		; byte 1
	push r1		; byte 2
	pop PC		; load r0r1 into PC - byte 3
	jmp execute_cmd.exit

; ************************************receiveChar *********************************
; Waits on the UART for a certain character (r2), character returned in A
; inputs:
; 	None
; outputs:
; 	received character in A 

receiveChar:
		mov A,F	;128 64 32 16 8  4   2  1
		;F7  F6 SD RDY OF N  C  Z
		and A,0x10 ; RX character is waiting
		jz receiveChar
	mov A,U		; get UART char
	pop T
	ret

load_failstr: dstr 'LOAD failed!'
load_waiting: dstr 'Waiting for handshake and transfer...'
load_complete: dstr 'Complete!'

execute_cmd.load:
	mov r0r1,load_waiting
	push_pc+1
	call print_str
	
; Put load destination address into r0r1
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
	
	; HANDSHAKE
	push_pc+1
	call receiveChar	
	cmp A,0x0A		; character returned in A
	jnz load.fail
	mov A,0xA0
	mov U,A			; send character back
	
	push_pc+1
	call receiveChar	
	cmp A,0x55		; character returned in A
	jnz load.fail
	mov A,0xAA
	mov U,A			; send character back
	
	push_pc+1
	call receiveChar	
	cmp A,0xAA		; character returned in A
	jnz load.fail
	mov A,0x55
	mov U,A			; send character back
	
	; SEND ADDRESS
	mov A,r0			; HIGH byte
	mov U,A
	push_pc+1
	call receiveChar
	cmp A,r0
	jnz load.fail
	
	mov A,r1			; LOW byte
	mov U,A
	push_pc+1
	call receiveChar
	cmp A,r1
	jnz load.fail
	
	mov U,'@'	; Acknowledge received and safe to send
	
	; Now receive the number of bytes (16-bit)
	push_pc+1
	call receiveChar	; High byte of num characters
	mov U,A			; send character back
	mov r2,A
	
	push_pc+1
	call receiveChar	; Low byte of num characters
	mov U,A			; send character back
	mov r3,A
	
	; If we got here then we shook hands and the destination address was received and num bytes
	
	loadloop:
		push_pc+1
		call receiveChar	; byte to writeex
		mov U,A			; echo character back
		
		mov [r0r1],A	; Write to memory.  We won't know if this character is wrong, but the programmer will
		inc r0r1
		
		dec r3		; dec r2r3
		mov A,r2
		subc A,0x00
		mov r2,A
		
		cmp A,0x00 ; is r2==0?
		jnz loadloop
		mov A,r3
		cmp A,0x00
		jnz loadloop
		
		; If we got here r2 = 0, r3 = 0, finished
	
	mov r0r1,load_complete
	push_pc+1
	call print_str
	
	jmp execute_cmd.exit
	
	load.fail:
		mov U,'!'	; means we failed
		mov r0r1, load_failstr
		push_pc+1
		call print_str
		jmp execute_cmd.exit

execute_cmd.beep:
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r0,r5		; HIGH of 10-bit n
	
	mov r4,[0x04]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x05]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov r1,r5		; LOW of 10-bit n
	
	push_pc+1
	call playbeep
	
	jmp execute_cmd.exit

add_cmd_full_str: dstr 'Command slots full!'
execute_cmd.add_cmd:
	mov r0r1,main_commands_jumptable
	
	mov A,COMMAND_TABLE_LEN
	cmp A,COMMAND_TABLE_LEN_MAX
	jge execute_cmd.add_cmd_full
	
	shl A	; index *2
	add A,r1
	mov r1,A
	mov A,r0
	addc A,0x00
	mov r0,A	;r0r1 = r0r1 + 2*index
	; Now we have the index into the address table
	
	; Get call address and add it to the call address jump table
	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov A,r5
	mov [r0r1],A		; HIGH of call address
	inc r0r1
	
	mov r4,[0x04]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x05]	; low hex nibble in ascii
	push_pc+1
	call ascii_hex_to_byte
	mov A,r5
	mov [r0r1],A		; LOW of call address
	
	mov r4r5,main_commands_table ; This contains addresses of strings
	mov A,COMMAND_TABLE_LEN
	shl A
	add A,r5
	mov r5,A
	mov A,r4
	addc A,0x00
	mov r4,A		; r2r3 = main_commands_table + 2*A = address of slot_n_str
	
	mov A,[r4r5]
	mov r2,A
	inc r4r5
	mov A,[r4r5]
	mov r3,A
	
	mov r0,[0x0E]	; source string in r0r1
	mov r1,[0x0F]
	
	copy_string: ; from r0r1 to r2r3 until zero character
	mov A,[r0r1]
	mov [r2r3],A
	mov U,A
	cmp A,0x00
	jz copy_string.exit
	inc r0r1
	inc r2r3
	jmp copy_string
	copy_string.exit:
	
	mov A,COMMAND_TABLE_LEN	; Increment number of commands in table
	inc A
	mov COMMAND_TABLE_LEN,A
	
	jmp execute_cmd.exit
	
	execute_cmd.add_cmd_full:
	mov r0r1, add_cmd_full_str
	push_pc+1
	call print_str
	jmp execute_cmd.exit

;execute_cmd.test_call:

	;push_pc+1		; ensures set PC to after call statement (3 bytes)
	;call draw_logo_2	; 0x@@ 0x@@@@
	
	;  This code means it is possible to CALL any given memory address and return correctly. 
	;  Alternatively, if the push_pc+1 is omitted, one can JMP to any given memory location
	
	; it means one could have a command which calls and returns to arbitary memory location, i.e.:
	; call 0x8234
	; could add functionality to load any given program (over UART) into a certain memory address and then run it
	
	;mov r0r1,draw_logo
	;push_pc+1	; push return address (3 bytes from here)
	;push r0		; byte 1
	;push r1		; byte 2
	;pop PC		; load r0r1 into PC - byte 3
	;jmp execute_cmd.exit


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

;####  General helper function cmp_str_special to compare two strings and save the special character # in the zero page.
;####	'*' means to save the rest of the string (points r0r1 to *)
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
	cmp A,0x2A ; *
	jz cmp_str_special.asterisk
	
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
cmp_str_special.asterisk:
	mov [0x0E],r2
	mov [0x0F],r3
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
	

welcome: dstr 'Welcome to Duncatron v1.0 - type "help" for commands'
ready: dstr 'READY'
NES_found: dstr 'NES controller found!'
interupt_text: dstr 'Interupt called!'
goodbye_str: dstr 'Bye!'
error_str: dstr 'ERROR'

; Logo generated here: https://patorjk.com/software/taag/#p=testall&f=Bulbhead&t=Duncatron%20
duncatron1_0: dstr '    ____                         __'                 
duncatron1_1: dstr '   / __ \__  ______  _________ _/ /__________  ____'     
duncatron1_2: dstr '  / / / / / / / __ \/ ___/ __ `/ __/ ___/ __ \/ __ \'     
duncatron1_3: dstr ' / /_/ / /_/ / / / / /__/ /_/ / /_/ /  / /_/ / / / /'     
duncatron1_4: dstr '/_____/\__,_/_/ /_/\___/\__,_/\__/_/   \____/_/ /_/' 

;Zero page structure:
; 0x00-0x01 RESERVED INT VECTOR
; 0x02-0x09 8 bytes for special str cmp
; 0x0A-0x0B programming current address (0x0A = High, 0x0B = Low byte)
; 0x0C		number of bytes for serial writing and reading
; 0x0D 		- CMD_TABLE_LENGTH
; 0x0E		- High byte of pointer to '*' position in string
; 0x0F 		- Low byte of pointer to '*' position in string
; data labels don't have to be page-aligned

0x8200:
input_str: db [129]; Need to have some kind of array notation for making fixed sizes, i.e. db [129]