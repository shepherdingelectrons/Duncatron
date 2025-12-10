NES_PORT equ [0x8100]
AUDIO_PORT equ [0x8101]
CONTROL_REG equ [0x8102] ; Control register 0b r7 56 r5 INT_EN SPI_EN SS2 SS1 SS0
SPI_PORT equ [0x8103] ; Check this is correct

OUT_PORT equ [0x8106]
IN_PORT equ [0x8107]

DS1302_SS equ 0x00  ; real-time control chip
SD_SS equ 0x01      ; SD card
FLASH equ 0x02 	    ; AT25DF081A EEPROM 1Mb (needs Vcc and/or signal voltage shifting)
MAX7219 equ 0x03

DS1302_seconds equ 0x01	; These values are already reversed to account for the LSB first requirement
DS1302_minutes equ 0x41	; of DS1302.  Most SPI devices are MSB first, which is what the hardware
DS1302_hours equ 0x21	; is designed to perform.
DS1302_dte equ 0x61	; we can parse the returned value in software to reverse it if we need to.
DS1302_month equ 0x11	; ok
DS1302_day equ 0x51
DS1302_year equ 0x31
DS1302_control equ 0x71
DS1302_trickle equ 0x09
DS1302_clkburst equ 0x7d

SPI.send: 	; The reason for breaking out such a simple function is that currently
			; nop instructions are required to ensure timings and that the SPI device has
			; completed sending before we read/send again.
			; In future hardware an extension shield will allow output of the control register
			; which will have #SPI_ACTIVE (or similar) routed to it
	mov SPI_PORT,A
	nop
	nop
	pop T
	ret

; DS1302 init 
DS1302.init:
	mov r0,DS1302_seconds
	push_pc+1
	call DS1302.read_register	; returns seconds register into r1
	
	mov A,r1
	and A,0xFE	; preserve seconds, clear clock halt in LSB if set (0b0000 0001 if CH set)
	mov r1,A
	
	;mov r0,DS1302_seconds
	;mov r1,0x00		; clear clock halt flag
	push_pc+1
	call DS1302.write_register	; r0 still set, r1 set
	
	pop T
	RET

DS1302.get_seconds:	; read seconds:
	mov r0,DS1302_seconds 
	push_pc+1
	call DS1302.read_register	
	; r1 returns value
	pop T
	RET

DS1302.write_register:
; write register:
; parameters:
; 	r0 = register to set
; 	r1 = value to set register to

mov A,DS1302_SS		
or A,0x08	
mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 1

mov A,r0			; WRITE register
push_pc+1
call SPI.send
	
mov A,r1			; r1 is data byte
push_pc+1
call SPI.send

mov A,DS1302_SS
mov CONTROL_REG,A	; SPI_EN = 0
pop T
RET

DS1302.read_register:
; read register:
; parameters:
; 	r0 = register to set
; output:
; 	r1 = return value of register

mov A,DS1302_SS		
or A,0x08	
mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 1

mov A,r0			; register to READ
or A,0x80			; set MSB to 1. DS1302 expects LSB first so this will set the LSB READ bit
push_pc+1			 
call SPI.send		

mov A,0xff			; dummy byte transfer
push_pc+1
call SPI.send

mov r1,SPI_PORT		; get MISO_byte into r1
mov A,DS1302_SS
mov CONTROL_REG,A	; SPI_EN = 0

pop T
RET

DS1302.burst_ushread:
; memory location to read data into is r2r3
	mov A,DS1302_SS		
	or A,0x08	
	mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 1
	
	mov r0,DS1302_clkburst
	push_pc+1			 
	call SPI.send	; start transaction

	mov r0,0x08
	DS1302.burst_read.loop:
		push_pc+1			 
		call SPI.send	; send dummy byte
		mov A,SPI_PORT	; read response
		mov [r2r3],A
		inc r2r3
		dec r0
		jnz DS1302.burst_read.loop

	mov A,DS1302_SS
	mov CONTROL_REG,A	; SPI_EN = 0
	
	pop T
	RET
