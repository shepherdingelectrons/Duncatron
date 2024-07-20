mov A,0x69
cmp A,0x69
jz skip
halt
skip:
mov A,0x60
loophere:
inc A
mov U,A
cmp A,0x69
jnz loophere

init:
mov r0r1,INTERUPT; setup interupt jump vector
mov [0x00],r0
mov [0x01],r1

mov A,0x55
mov B,0xAA
mov A,0x00
mov A,B
mov B,0x00
mov B,0x55

mov B,0x02
mov A,0x09
add A,B
cmp A,0x0B

countup:
inc A
;jmp countup

test_stack:
mov r0,0x69
mov r1,0x42
mov r2,r0
push r2
pop A
mov A,[0x00] ; zero page read (INTERUPT address)
mov A,[0x01] ;
push r3
pop r2

mov U,0x0A	; newline
mov U,0x0D

mov r0r1,welcome	; PRINT welcome message
push_pc+1
call print_str

push_PC+1	; Test interupt calling manually
int 

main:
mov r0r1,helloworld
push_PC+1
CALL print_str

jmp main

print_int:
mov r0r1,interupt_text
PUSH_PC+1
call print_str
POP T
RET

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

INTERUPT:
PUSH_PC+1
call print_int	; call a function from within the interupt to test
RETI

; data labels don't have to be page-aligned
welcome:
dstr 'Welcome to Duncatron v1.0'
helloworld:
dstr 'Hello world @=)'
interupt_text:
dstr 'Interupt called!'