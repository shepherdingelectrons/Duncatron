init:
mov r0r1,INTERUPT; setup interupt jump vector
mov [0x00],r0
mov [0x01],r1
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
main:
push_PC+1
int 
mov A,0x65 ; e
mov A,0x6c ; l
mov A,0x6c ; l
mov A,0x6f ; o
mov A,0x20 ; ' '
mov A,0x6a ; j
mov A,0x61 ; a
mov A,0x7a ; z
mov A,0x7a ; z
mov A,0x79 ;y
nop;halt
jmp main

print_welcome:
mov r0r1,0x0100
mov A,[r0r1]
mov r0r1,0x0101
mov A,[r0r1]
mov r0r1,0x0102
mov A,[r0r1]
mov r0r1,0x0103
mov A,[r0r1]
mov r0r1,0x0104
mov A,[r0r1]
mov r0r1,0x0105
mov A,[r0r1]
mov r0r1,0x0106
mov A,[r0r1]
POP T
RET

INTERUPT:
PUSH_PC+1
call print_welcome
mov A,0x48 ; 'H'
RETI

0x0100: 
; data labels don't have to be page-aligned
welcome:
dstr 'Welcome to Duncatron v1.0'
hello:
dstr 'Hello'
world:
dstr 'world'
interupt_text:
dstr 'Interupt called!'