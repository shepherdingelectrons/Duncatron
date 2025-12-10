cmd.reverse_byte:

	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
	mov r5,[0x03]	; low hex nibble in ascii
	push_pc+1
	call 0x082d ;ascii_hex_to_byte
	mov r2,r5
	
	push_pc+1
	call reverse_byte
	
	mov r4,A	; A contains reversed byte
	mov r5,0x01
	push_pc+1
	call 0x07d2 ;print_hex
	mov U,0x0A
	mov U,0x0D

	pop T
	RET


reverse_table:
db 0x00,0x08,0x04,0x0c,0x02,0x0a,0x06,0x0e,0x01,0x09,0x05,0x0d,0x03,0x0b,0x07,0x0f
reverse_byte:
; parameters:
; 	r2 - byte to reverse
; uses:
;	r0r1 as pointer
; returns:
;	A

;	mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
;	mov r5,[0x03]	; low hex nibble in ascii
;	push_pc+1
;	call 0x082d ;ascii_hex_to_byte
;	mov r2,r5
	
mov r0r1,reverse_table
mov A,r2
and A,0x0f	; get lower nibble
add A,r1
mov r1,A
mov A,r0
addc A,0x00
mov r0,A

mov A,[r0r1]
shl A
shl A
shl A
shl A	; shift answer left 4
push A

mov r0r1,reverse_table
mov A,r2
shr A
shr A
shr A
shr A	; get upper nibble
add A,r1
mov r1,A
mov A,r0
addc A,0x00
mov r0,A

mov A,[r0r1]
pop B
or A,B	; A contains final result

pop T
RET