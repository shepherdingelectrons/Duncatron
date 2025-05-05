mov A,0xAA
mov B,0x55

print_str_safe:
mov r0r1,string

print_str_safe.loop:
	mov A,[r0r1]
	cmp A,0x00	; check for end of string
	jz eostr
	push A
	;mov r2,A
	wait_to_send:
	mov A,F
	and A,0x20 ; TX sending
	jnz wait_to_send ; loop if TX is active
	pop A
	;mov A,r2
	mov U,A
	inc r0r1
	jmp print_str_safe.loop

eostr:
;mov U,0x0A ; won't be TX safe oh well
;mov U,0x0D

mov A,U ;Clear RX

wait_char:
mov A,F
and A,0x10 ; RX character is waiting
jz wait_char
mov A,U	; READ character
mov U,A ; send character
jmp wait_char

HALT

string: dstr 'READY'
