NES_PORT equ [0x8100]
AUDIO_PORT equ [0x8101]
CONTROL_REG equ [0x8102] ; Control register 0b r7 56 r5 INT_EN SPI_EN SS2 SS1 SS0
SPI_PORT equ [0x8103] ; Check this is correct

OUT_PORT equ [0x8106]
IN_PORT equ [0x8107]

DS1302_SS equ 0x00  ; real-time control chip
SD_SS equ 0x01      ; SD card
FLASH_SS equ 0x02 	    ; AT25DF081A EEPROM 1Mb (needs Vcc and/or signal voltage shifting)
MAX7219_SS equ 0x03

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

DS1302_RAM0 equ 0x03 ; 0b1100 0000 

;MAX7219
MAX7219_DECODE equ 0x09                        
MAX7219_INTENSITY equ 0x0a                       
MAX7219_SCAN_LIMIT equ 0x0b                       
MAX7219_SHUTDOWN equ 0x0c                      
MAX7219_DISPLAY_TEST equ 0x0f                       

MAX7219_INTENSITY_MIN equ 0x00                       
MAX7219_INTENSITY_MAX equ 0x0f    

max7219_loop:
	push_pc+1
	call max7219_init
	
	mov r3,0x00
	mov r4r5,digit_sequence
	
	clock_loop:
		mov A,F	;128 64 32 16 8  4   2  1
		;F7  F6 SD RDY OF N  C  Z
		and A,0x10 ; RX character is waiting
		jnz clock_loop.exit
		
		push_pc+1
		call DS1302.get_seconds	; uses r0,r2 and returns in r1
		mov [0x8106],r1
		
		;mov A,r3 	;previous seconds
		;cmp A,r1
		;je clock_loop
		
		;mov r3,r1	; update seconds 
		
		mov r3,0x01
		push r4
		push r5
	
	set_digits:
		mov A,[r4r5]		
		mov r2,MAX7219_SS
		mov r0,r3;0x01
		mov r1,A
		push_pc+1
		call SPI.write_register
		
		inc r4r5
		
		mov r0r1,end_digit_sequence
		mov A,r5
		cmp A,r1
		
		mov A,r4
		cmpc A,r0 ; 16-bit compare
		jl set_digits_no_overflow
		
		mov r4r5,digit_sequence
	
	set_digits_no_overflow:
		inc r3
		mov A,r3
		cmp A,0x05
		jne set_digits
	pop r5
	pop r4
	inc r4r5
	
	mov r0r1,end_digit_sequence
	mov A,r5
	cmp A,r1
	
	mov A,r4
	cmpc A,r0 ; 16-bit compare
	jl clock_loop
	mov r4r5,digit_sequence
	
	jmp clock_loop
		
clock_loop.exit:	
	mov A,U
	pop T 
	RET
digit_sequence:
db 0x40,0x20,0x10,0x08,0x04,0x02
end_digit_sequence:
 
max7219_init:
	mov r2,MAX7219_SS
	mov r0,MAX7219_SCAN_LIMIT
	mov r1,0x07
	push_pc+1
	call SPI.write_register
	
	mov r0,MAX7219_DECODE
	mov r1,0x00
	push_pc+1
	call SPI.write_register
	
	mov r0,MAX7219_SHUTDOWN
	mov r1,0x01
	push_pc+1
	call SPI.write_register
	
	mov r0,MAX7219_DISPLAY_TEST
	mov r1,0x00
	push_pc+1
	call SPI.write_register
	
	mov r0,MAX7219_INTENSITY
	mov r1,MAX7219_INTENSITY_MAX
	push_pc+1
	call SPI.write_register
	
	pop T
	RET
	
ds1302_loop:
	push_pc+1
	call DS1302.init
	
	sec_loop:
		mov A,F	;128 64 32 16 8  4   2  1
		;F7  F6 SD RDY OF N  C  Z
		and A,0x10 ; RX character is waiting
		jnz sec_loop.exit
		
		push_pc+1
		call DS1302.get_seconds
		mov [0x8106],r1
		jmp sec_loop
		
sec_loop.exit:
pop T
RET

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
	mov r2,DS1302_SS
	mov r0,DS1302_seconds
	push_pc+1
	call SPI.read_register	; returns seconds register into r1
	
	mov A,r1
	and A,0xFE	; preserve seconds, clear clock halt in LSB if set (0b0000 0001 if CH set)
	mov r1,A
	
	;mov r0,DS1302_seconds
	;mov r1,0x00		; clear clock halt flag
	push_pc+1
	call SPI.write_register	; r0 still set, r1 set and r2
	
	pop T
	RET

DS1302.get_seconds:	; read seconds:
	mov r2,DS1302_SS
	mov r0,DS1302_seconds 
	push_pc+1
	call SPI.read_register	
	; r1 returns value
	pop T
	RET

SPI.write_register:
; write register:
; parameters:
; 	r0 = register to set
; 	r1 = value to set register to
;	r2 = Slave Select number

mov A,r2		
or A,0x08	
mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 1

mov A,r0			; WRITE register
push_pc+1
call SPI.send
	
mov A,r1			; r1 is data byte
push_pc+1
call SPI.send

mov CONTROL_REG,r2	; SPI_EN = 0
pop T
RET

SPI.read_register:
; read register:
; parameters:
; 	r0 = register to set
;	r2 = Slave Select device
; output:
; 	r1 = return value of register

mov A,r2		
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
mov CONTROL_REG,r2	; SPI_EN = 0

pop T
RET

DS1302.burst_read:
; memory location to read data into is r2r3
	mov A,DS1302_SS		
	or A,0x08	
	mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 1
	
	mov A,DS1302_clkburst
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
