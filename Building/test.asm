init:
mov r0r1,INTERUPT; setup interupt jump vector
mov [0x00],r0	; Zero page 0x00
mov [0x01],r1	; Zero page 0x01

mov r0r1,ready	; Print a greeting message
push_pc+1
call print_str

; New string:
mov r2r3,input_str
mov r4,0x00
mov U,0x3E ; ">"

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
jz main.exit

; Else, command not found
mov r0r1,error_str
push_pc+1
call print_str

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



; data labels don't have to be page-aligned
welcome:
dstr 'Welcome to Duncatron v1.0'
ready:
dstr 'READY'
helloworld:
dstr 'Hello world @=)'
interupt_text:
dstr 'Interupt called!'
exit_str:
dstr 'exit'
goodbye_str:
dstr 'Bye!'
error_str:
dstr 'ERROR'
input_str: ;
