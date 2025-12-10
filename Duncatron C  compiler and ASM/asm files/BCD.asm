BCD_digits equ 0x8400

printBCD_16bit:
; input:
; 	r0r1 = 2-byte value
; uses:

; double dabble algorithm:
; (1) shift everything left.
; (2) If any of the nibbles are >=5 then add 3 (with c)
; (3) loop 8 times

;initialise, clear scratch memory 
;mov r0,0xA5
;mov r1,0x5A
mov r4,[0x02]	; high hex nibble in ascii, 0-9/a-f/A-F
mov r5,[0x03]	; low hex nibble in ascii
push_pc+1
call 0x082d ;ascii_hex_to_byte
mov r1,r5
	
mov r4,[0x04]	; high hex nibble in ascii, 0-9/a-f/A-F
mov r5,[0x05]	; low hex nibble in ascii
push_pc+1
call 0x082d ;ascii_hex_to_byte
mov r0,r5
	
mov r4,0x05		; 16 bits use 5 bytes of representation in binary
mov r2r3,BCD_digits	; some kind of memory scratch space
clear_mem_loop:
	mov [r2r3],0x00	; ones
	inc r2r3
	dec r4
	jnz clear_mem_loop


mov r5,0x10;10	; shift loop counter = 16
printBCD.shift_loop:
	mov A,r1
	shl A	;sets carry
	push F	; put r1 flag onto stack for later
	mov r1,A
	
	mov A,r0
	shl A	; r0 carry is set
	mov r0,A
	
	mov A,r1
	addc A,0x00	; A is r1<<1 + carry
	mov r1,A
	
	mov r4,0x05		; 16 bits use 5 bytes of representation in binary
	mov r2r3,BCD_digits
	printBCD_digitshift_loop:
		mov A,[r2r3]
		shl A
		pop F
		addc A,0x00		; add carry to value 
		mov [r2r3],A
		
		shl A
		shl A
		shl A
		shl A
		push F			; save carry flag
		
		mov A,[r2r3]	; limit to 4-bit nibble		
		and A,0x0F
		mov [r2r3],A
		
		cmp A,0x05
		jl printBCD_nextdigit
		; If we're here then A is >=5
		
		mov A,r5
		cmp A,0x01
		je printBCD_nextdigit ; skip if on last shift
		
		mov A,[r2r3]
		add A,0x03
		mov [r2r3],A
		
		printBCD_nextdigit:
		
		inc r2r3
		dec r4
		jnz printBCD_digitshift_loop
		pop F
	
	dec r5
	jnz printBCD.shift_loop
	
; display r0 and r1 for now

;mov r4,0x05		; 16 bits use 5 bytes of representation in binary
mov r2r3,BCD_digits
mov r3,0x04		; assumes BCD_digits is "page-aligned"
mov r5,0x00		; leading zero-flag

print_BCDdigits:
	mov A,r5
	cmp A,0x00
	jne zerotrail_false
	; if we're here then we haven't had a non-zero digit yet...
	mov A,[r2r3]	; get digit
	cmp A,0x00		; is it zero?
	je zero_digit
	mov r5,0x01
	
	zerotrail_false:
		mov A,[r2r3]
		add A,0x30	;'0'
		mov U,A
	
	zero_digit:
		dec r3	
		jc print_BCDdigits ; carry is set differently for subtractions/decs
		; Think of carry as "not borrow"
mov A,r5
cmp A,0x00
jne BCD_digits_exit
mov U,'0'
BCD_digits_exit:
pop T
ret