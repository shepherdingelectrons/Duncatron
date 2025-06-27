SOUND_PORT equ 0x8101

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
	
sound_on:
	mov A,0x90
	mov [SOUND_PORT],A
	;mov A,0xBF
	;mov [SOUND_PORT],A
	;mov A,0xDF
	;mov [SOUND_PORT],A
	;mov A,0xFF
	;mov [SOUND_PORT],A
	pop T
	ret