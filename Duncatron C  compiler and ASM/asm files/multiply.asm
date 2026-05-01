print_hex_ROM equ 0x07d2

; multiply algorithm
; r0 * r1 = r3r4
mul8x8:
mov r0,0xff
mov r1,0xff ; 0x34*0x23 = 0x07 1c

mov r2,0x00	; r2r1 is used as the shifted r1

mov r3,r2		; result register r3r4 = 0x0000
mov r4,r2

mov r5,0x01	; start with first bit 1st bit

mul8x8_loop:
	mov A,r0
	mov B,r5
	and A,B		; performs a mask based on which bit to currently examine
	
	jz shift_r2r1
	; else add the shifted value of r2r1 to the result register r3r4
	mov A,r4
	add A,r1
	mov r4,A
	mov A,r3
	addc A,r2
	mov r3,A
	
	shift_r2r1:
	;shift r1 left 1 and into r2
	mov A,r2
	shl A
	mov r2,A
	
	mov A,r1
	shl A
	mov r1,A 	; carry bit set
	
	mov A,r2
	addc A,0x00
	mov r2,A	; move carry bit from r1 shift into r2 (which has already been shifted)

	mov A,r5
	shl A
	mov r5,A		; r5 = r5<<1 
	jnz mul8x8_loop	; when we shift out the last time, the register will be zero

; answer in r3r4
push r4
mov r4,r3
mov r5,0x01
push_pc+1
call print_hex_ROM

pop r4
mov r5,0x00
push_pc+1
call print_hex_ROM

pop T
RET