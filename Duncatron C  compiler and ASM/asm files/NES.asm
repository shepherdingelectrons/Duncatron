NES_PORT equ [0x8100]
AUDIO_PORT equ [0x8101]
CONTROL_REG equ [0x8102] ; Control register 0b r7 56 r5 INT_EN SPI_EN SS2 SS1 SS0
SPI_PORT equ [0x8103] ; Check this is correct

OUT_PORT equ [0x8106]
IN_PORT equ [0x8107]

musical_NES:
		mov r5,0x00 ; midi channel
NES_loop:
		push_pc+1
		call 0x0682 ; MIDI_monitor : 0x682
		
		mov A,F	;128 64 32 16 8  4   2  1
		;F7  F6 SD RDY OF N  C  Z
		and A,0x10 ; RX character is waiting
		jnz NES_loop.exit
		
		; do stuff
		mov A,NES_PORT
		mov B,A
		not A	; bug in current implementation of ALU, is actually not B...
		mov OUT_PORT,A

		push A
		
		mov r2r3,NES_notes
		mov r4,0x08 ; test 8 buttons
		
		
		NES_testbyte_loop:
			pop A
			shl A	; carry flag can be set
			push A

			jnc no_button
			; else a button was pressed
			mov A,[r2r3]
			
			mov r0,A	; midi note
			mov r1,0x01	; midi note duration
			;mov r5,0x00	; midi channel
			push_pc+1
			call 0x06f9	; playMIDI : 0x6f9
			inc r5 ; next channel
			and A,0x02	; A will hold r5, limit to range 0-2
			mov r5,A
			
			no_button:
			inc r2r3
			dec r4
			jnz NES_testbyte_loop
			
		pop A ; restore stack
	jmp NES_loop
	
	NES_loop.exit:
	pop T
	RET

NES_notes:
db 0x42,0x44,0x46,0x47,0x49,0x4b,0x4d,0x4e