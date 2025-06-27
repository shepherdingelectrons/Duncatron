;.include "SystemOS.asm"	; makes sure references from bios functions are exposed

; Entry point to function is here
blah:
mov A,0x05
myfunction:	

mov U,'Y'
mov U,'o'
mov U,'!'
mov U,0x0A
mov U,0x0D
mov U,'H'
mov U,'e'
mov U,'h'
mov U,'e'

dec A
jnz myfunction

pop T
RET		; function is 26 bytes

; Therefore this should start at 0x831a
echo_function:
	mov U,0x0A
	mov U,0x0D
	
	mov r0,[0x0E]	; source string in r0r1
	mov r1,[0x0F]
	
	display_string: ; from r0r1 to r2r3 until zero character
	mov A,[r0r1]
	mov U,A
	cmp A,0x00
	jz display_string.exit
	inc r0r1
	inc r2r3
	jmp display_string
	
	display_string.exit:
	mov U,0x0A
	mov U,0x0D
	
	pop T
	ret


