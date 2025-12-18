

testALU:
; Loop through alu tests, perform, compare results for calculation and carry flag
mov r0r1, alu_tests

mov A,0x01	
add A,0x00	; clears carry and zero flag
push F 	; push flags

testALU.loop:
	mov A,[r0r1]
	mov r2,A	; ALU test function in r2

	cmp A,0xff
	je testALU.termination_character
	
	inc r0r1
	mov A,[r0r1]
	mov r3,A	; "A" = r3
	
	;print "A" - beware of registers used in print_hex
	mov r4,r3	;
	mov r5,0x01	; print leading '0x'
	push_pc+1 
	call 0x07d2 ; print_hex (uses r4 and r5)
	
	inc r0r1
	mov A,[r0r1]
	mov r4,A	; "B" = r4
	
	mov A,r2
	cmp A,0x00	; "add" sets flags
	mov A,r3
	mov B,r4
	je alu_add

	mov A,r2
	cmp A,0x01	; "sub" sets flags
	mov A,r3
	mov B,r4
	je alu_sub
	
	mov A,r2
	cmp A,0x02	; "addc" sets flags
	mov A,r3
	mov B,r4
	je alu_addc
	
	mov A,r2
	cmp A,0x03	; "addc" sets flags
	mov A,r3
	mov B,r4
	je alu_subc

	jmp testALU.test_not_supported ; 

alu_add:
	pop F
	add A,B	; sets flags
	mov U,'+'
	jmp handle_result

alu_sub:
	pop F
	sub A,B	; sets flags
	mov U,'-'
	jmp handle_result
	
alu_addc:
	pop F
	addc A,B	; sets flags
	mov U,'+'
	mov U,'c'
	mov U,'+'
	jmp handle_result
	
alu_subc:
	pop F
	subc A,B	; sets flags
	mov U,'-'
	mov U,'c'
	mov U,'-'
	jmp handle_result
	
handle_result:
	push F	; save the flag register so that we can chain add, addc, subc cmpc etc
	;push A	; calculation result
	mov r3,A ; save calculation result in r3
	mov A,F
	mov r2,A 	; save new flags in r2 for comparison later
	
	;print "B" - beware of registers used in print_hex
	; r4 still equals B
	mov r5,0x01	; print leading '0x'
	push_pc+1 
	call 0x07d2 ; print_hex (uses r4 and r5). r4 is NOT modified
	
	mov U,'='

	mov r4,r3	; print calculation result 
	mov r5,0x01
	push_pc+1 
	call 0x07d2 ; print_hex (uses r4 and r5). r4 is NOT modified
	
	inc r0r1
	mov A,[r0r1]
	mov r4,A	; expected result 
	mov r5,0x01
	mov U,'('
	push_pc+1 
	call 0x07d2 ; print_hex of expected result
	mov U,')'
	
	mov A,r3 ; calculation result
	cmp A,r4 ; compare to expected result
	jne alu_not_expected
	;jmp alu_expected
	
alu_expected:
;print "OK!"
	
	mov U,'O'
	mov U,'K'
	mov U,' '
; look at flags
	;F7  F6 SD RDY OF N  C  Z

	
	inc r0r1	; move onto expected carry result
	mov A,[r0r1] ; expected carry
	mov r3,A
	
	mov A,r2	; flag from calculation
	shr A
	and A,0x01	; prepare carry from actual calculation
	mov r2,A
	
	mov U,'C'
	mov U,'='
	mov r4,r2
	mov r5,0x01
	push_pc+1 
	call 0x07d2 ; print_hex of measured carry
	
	mov U,'('
	mov r4,r3 	; expected carry
	mov r5,0x01
	push_pc+1 
	call 0x07d2 ; print_hex of measured carry
	mov U,')'
	
	;mov r2,0x01
	;mov r3,0x00
	mov A,r2
	;mov B,r3
	cmp A,r3 ; cmp A,B works
	jnz carry_mismatch
	; carry matches
	
	mov U,'O'
	mov U,'K'
	
	mov U,0x0A
	mov U,0x0D
	
	inc r0r1
	jmp testALU.loop
	
	carry_mismatch: ; no carry match
	mov U,' '
	mov U,'X'
	mov U,0x0A
	mov U,0x0D
	
	inc r0r1
	jmp testALU.loop

alu_not_expected:
;print "expected this, got this"
	inc r0r1
	mov A,[r0r1]	; carry flag expected
	
	mov U,'N'
	mov U,'O'
	mov U,0x0A
	mov U,0x0D
	inc r0r1
	jmp testALU.loop

testALU.test_not_supported:;print "ALU test function not supported"
	pop F
	mov U,'?'
	mov U,'?'
	mov U,'?'
	
	mov U,0x0A
	mov U,0x0D
	jmp alu_test.exit
	
testALU.termination_character:
	pop F
	mov U,':'
	mov U,')'
	
alu_test.exit:
pop T
RET

; 
; 0 - add A,B
; 1 - sub A,B
; 2 - cmp A,B
; 3 - dec A

ADD_CMD equ 0x00
SUB_CMD equ 0x01
ADDC_CMD equ 0x02
SUBC_CMD equ 0x03

alu_tests:
db ADD_CMD,0xff,0x02,0x01,0x00	; alu function,A,B,expected result,Carry flag
db ADD_CMD,0xff,0x01,0x00,0x00	; alu function,A,B,expected result,Carry flag
db ADD_CMD,0xff,0x00,0xff,0x01	; alu function,A,B,expected result,Carry flag
db ADD_CMD,0x01,0x02,0x03,0x01	; alu function,A,B,expected result,Carry flag
db SUB_CMD,0x02,0x01,0x01,0x00	; sub 2,1 = 1 nc
db SUB_CMD,0x04,0x05,0xff,0x01 ; 
db ADD_CMD,0xff,0x01,0x00,0x00 ; add
db ADDC_CMD,0x04,0x02,0x07,0x01 ; addc 
db SUB_CMD,0x00,0x02,0xfe,0x01 ; sub
db SUBC_CMD,0x0A,0x01,0x08,0x00 ; subc

; could push the flag register so that can use for cmpc, subc, addc, etc instructions
db 0xff; termination character
; testing ALU functions