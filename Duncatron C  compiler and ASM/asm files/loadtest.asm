;.include "SystemOS.asm"	; makes sure references from bios functions are exposed

SOUND_PORT equ 0x8101
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
