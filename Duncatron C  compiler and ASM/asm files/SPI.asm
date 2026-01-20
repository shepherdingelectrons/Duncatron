NES_PORT equ [0x8100]
AUDIO_PORT equ [0x8101]
CONTROL_REG equ [0x8102] ; Control register 0b r7 56 r5 INT_EN SPI_EN SS2 SS1 SS0
SPI_PORT equ [0x8103] ; Check this is correct

OUT_PORT equ [0x8106]
IN_PORT equ [0x8107]

SD_LOW_CAPACITY equ [0xff]

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

print_hex_ROM equ 0x07d2
print_str_ROM equ 0x07c1

SD_CMD0:  db 0x40,0x00,0x00,0x00,0x00,0x95
SD_CMD8:  db 0x48,0x00,0x00,0x01,0xAA,0x87
SD_CMD58: db 0x7A,0x00,0x00,0x00,0x00,0x95 ; or is CRC 0x75??
SD_CMD55: db 0x77,0x00,0x00,0x00,0x00,0x65
SD_CMD41_HCS: db 0x69,0x40,0x00,0x00,0x00,0x77
SD_CMD41: db 0x69,0x00,0x00,0x00,0x00,0xE5
SD_CMD16: db 0x50,0x00,0x00,0x02,0x00,0xFF
SD_CMD59: db 0x7B,0x00,0x00,0x00,0x00,0xFF
SD_CMD1:  db 0x41,0x00,0x00,0x00,0x00,0xF9
SD_RESPONSE: db 0x00,0x00,0x00,0x00,0x00 	; make sure this ends up going into RAM and not ROM on hardware


SDcard.mount:
	SDcard.loop:
	mov U,0x0A
	mov U,0x0D
	
	mov r1,0xff	; exit code
	
		mov A,F	;128 64 32 16 8  4   2  1
		;F7  F6 SD RDY OF N  C  Z
		and A,0x10 ; RX character is waiting
		jnz SDcard.loop.exit
	
	push_pc+1
	call SD.init

	mov r0r1,SD_CMD0
	push_pc+1
	call SD_sendCMD
	mov r1,0x00	; return code if necessary
	mov A,r0
	cmp A,0x01
	jne SDcard.CMD_failed
	; CMD0 returned 0x01 (success)
	
	mov r0r1,SD_CMD8
	push_pc+1
	call SD_sendCMD
	mov r1,0x08	; return code if necessary
	mov A,r0
	cmp A,0x01 ; might also be 0x05?
	jne SDcard.CMD_failed
	; CMD8 returned 0x01 (success)
	
	mov r0r1,SD_CMD58
	push_pc+1
	call SD_sendCMD
	mov r1,0x3A	; return code if necessary
	mov A,r0
	cmp A,0x01
	jne SDcard.CMD_failed	
	; CMD58 returned 0x01
	
	mov r0r1,SD_RESPONSE	; https://github.com/h0m3/SDCore/blob/master/SDCore.cpp
	inc r0r1
	mov A,[r0r1]	; get second received byte
	and A,0x40		; SDCore::low_capacity = !(SPDR && 0x40);
	mov B,A
	not A		; bug in hardware, actually does not B
	mov SD_LOW_CAPACITY,A ; card low_capacitiy 
	
	inc r0r1
	mov A,[r0r1]	; get third received byte
	and A,0x78
	mov r1,0x78		; r1 changes, don't access r0r1 again
	jz SDcard.CMD_failed	; zero is bad, return r1 set as 0x78
	
	SD_CMD55_loop:	; doesn't actually loop for now.
	
	mov r0r1,SD_CMD55
	push_pc+1
	call SD_sendCMD
	mov r1,0x37	; return code if necessary
	mov A,r0
	cmp A,0x05
	jne SDcard.CMD55_not_five
	; CMD55 reply is 0x05
	; support older cards
		mov r0r1,SD_CMD1
		push_pc+1
		call SD_sendCMD
		mov r1,0x01
		mov A,r0
		cmp A,0x00
		jz SDcard.CMD55_OK
		jmp SDcard.CMD_failed
		
	SDcard.CMD55_not_five:
		mov r0r1,SD_CMD41_HCS	; Run ACMD41 with arg 0x40000000 for HCS cards
		push_pc+1
		call SD_sendCMD
		mov r1,0x29	; = 41
		mov A,r0
		cmp A,0x00
		jz SDcard.CMD55_OK
		
		; Run ACMD41 for any other card
		mov r0r1,SD_CMD55
		push_pc+1
		call SD_sendCMD
		
		mov r0r1,SD_CMD41
		push_pc+1
		call SD_sendCMD
		mov r1,0x2A	; = 42 (to distinguish from other CMD41 call)
		mov A,r0
		cmp A,0x00
		jz SDcard.CMD55_OK
		jmp SDcard.CMD_failed
		
SDcard.CMD55_OK:
	mov r0r1,CMD_success
	push_pc+1
	call print_str_ROM
	
	; this is where we would do the final setup stuff
	mov r0r1,SD_CMD16	; Set block size to 512 bytes
	push_pc+1
	call SD_sendCMD
	mov r1,0x10
	mov A,r0
	cmp A,0x00
	jnz SDcard.CMD_failed
	
	mov r0r1,SD_CMD59	; Disable CRC checking
	push_pc+1
	call SD_sendCMD
	mov r1,0x3B
	mov A,r0
	cmp A,0x00
	jnz SDcard.CMD_failed
	
	; if got here then all good!
	jmp SDcard.loop

SDcard.CMD_failed:
; Could print r0 and r1 codes
mov U,0x0A
mov U,0x0D	; r1 contains exit code

; DEBUG
mov r4,r0
mov r5,0x01
push_pc+1
call print_hex_ROM

; DEBUG
mov r4,r1
mov r5,0x01
push_pc+1
call print_hex_ROM

mov U,0x0A
mov U,0x0D

jmp SDcard.loop	; for now just re-enter loop if fails
pop T
RET

CMD_success: dstr 'CMD0/8/58: ok!'

SDcard.loop.exit:	; clean exit 
mov U,0x0A
mov U,0x0D
pop T
RET

SD.init:
	; https://www.dejazzer.com/ee379/lecture_notes/lec12_sd_card.pdf
	;"To communicate with the SD card, your program has to place the SD card into the SPI mode.
	; To do this, set the MOSI and CS lines to logic value 1 and toggle SD CLK for at least 
	; 74 cycles. After the 74 cycles (or more) have occurred, your program should set the CS 
	; line to 0 and send the command CMD0
	
	mov r0,0x0A	; send 10 bytes
	mov A,SD_SS
	mov CONTROL_REG,A	; SPI_EN = 0, CS not enabled
	
	SD.init.byteloop:
		mov A,0xFF
		push_pc+1
		call SPI.send
		dec r0
		jnz SD.init.byteloop
	pop T
	RET

SD_sendCMD:
; r0r1 - pointer to 6 byte memory location of command
; r0 - return byte with received byte
mov U,0x0A
mov U,0x0D

mov r2,0x06

mov A,SD_SS
or A,0x08	; SPI_EN = 1
mov CONTROL_REG,A

SD_sendCMD.loop:
	mov A,[r0r1]
	push_pc+1
	call SPI.send
		
	inc r0r1
	dec r2
	jnz SD_sendCMD.loop

mov r2,0x08	; Read 8 bytes and return first byte that isn't 0xff
SD_sendCMD.MISOloop:
	mov A,0xFF	; receive byte
	push_pc+1
	call SPI.send
	
	mov A,SPI_PORT
	cmp A,0xFF
	jne SD_sendCMD.getMISO	; found first non-0xFF byte
	
	dec r2
	jnz SD_sendCMD.MISOloop
	
	mov A,SPI_PORT	; get last received byte (will be 0xFF)
	push A 			; becomes return byte
	jmp SD_sendCMD.exit ; if we got here then only 0xFF received, switch off SPI and exit

SD_sendCMD.getMISO:
	mov r0r1,SD_RESPONSE
	mov A,SPI_PORT
	push A	; save first received byte onto stack for return byte
	
	mov [r0r1],A	; save into SD_RESPONSE buffer
	; DEBUG
	mov r4,A
	mov r5,0x01
	push_pc+1
	call print_hex_ROM
	;
	inc r0r1
	
	mov r2,0x04	; Read next 4 bytes of response
	SD_sendCMD.getMISOloop:
		mov A,0xFF	; receive byte
		push_pc+1
		call SPI.send
		
		mov A,SPI_PORT
		mov [r0r1],A
		
		; DEBUG
		mov r4,A
		mov r5,0x01
		push_pc+1
		call print_hex_ROM
		
		inc r0r1
		dec r2
		jnz SD_sendCMD.getMISOloop
	
SD_sendCMD.exit:
pop r0
mov A,SD_SS		
mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 0

pop T
RET

max7219_loop:
	push_pc+1
	call DS1302.init
	
	push_pc+1
	call max7219_init
	
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

; DS1302 init `
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
