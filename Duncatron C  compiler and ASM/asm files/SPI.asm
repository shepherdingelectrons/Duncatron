NES_PORT equ [0x8100]
AUDIO_PORT equ [0x8101]
CONTROL_REG equ [0x8102] ; Control register 0b r7 56 r5 INT_EN SPI_EN SS2 SS1 SS0
SPI_PORT equ [0x8103] ; Check this is correct

OUT_PORT equ [0x8106]
IN_PORT equ [0x8107]


SD_RESERVED_SECTORS_MSB equ [0xfa]
SD_RESERVED_SECTORS_LSB equ [0xfb]
SD_FAT_SIZE_SECTORS_MSB equ [0xfd]
SD_FAT_SIZE_SECTORS_LSB equ [0xfe]

SD_CURRENT_PARTITION equ [0xf6]
SD_SECTOR_SIZE equ 0x80f7	; 2 bytes
SD_SECTORS_PER_CLUSTER equ 0x80f9 ; 1 byte
SD_RESERVED_SECTORS equ 0x80fa	; 2 bytes
SD_NUM_FATS equ 0x80fc	; 1 byte
SD_FAT_SIZE_SECTORS equ 0x80fd	; 2 bytes
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
SD_CMD17: db 0x51,0x00,0x00,0x00,0x00,0xFF
SD_BLOCK equ 0x8300 ; RAM

SD_PARTITIONS equ 0x8500	
;SD_PARTITIONS equ 0xf0 ; 3 bytes per partition with start block in (or zero)
; 0x00 - partition 0 valid/invalid 
; 0x01-0x03 partition 0 starting block
; 0x04 - partition 1 valid/invalid 
; 0x05-0xf7 partition 1 starting block
; 0x08 - partition 2 valid/invalid 
; 0x09-0x0b partition 2 starting block
; 0x0c - partition 3 valid/invalid 
; 0x0d-0x0f partition 3 starting block
SD_ROOT_ADDRESSES equ 0x8510	; 4 partitions * [32-bit address (4 bytes) + 1] = 20 bytes
; +0 - valid/invalid root 0 address
; +1-4 root address (big endian)
; +5 - valid/invalid root 1 address
; +6-9 root address (big endian)
; +10 - valid/invalid root 2 address
; +11-14 root address (big endian)
; +15 - valid/invalid root 3 address
; +16-19 root address (big endian)

SDcard.test:
	push_pc+1
	call SD.reset_memory_tables
	
	mov r0r1,&'\nInitialising SD card...\n'
	push_pc+1
	call print_str_ROM
	push_pc+1
	call SDcard.mount
	mov A,r0 ; returns r0 = 0 for success, or 1 for error
	cmp A,0x00
	jnz SDcard.error
	
	mov r0r1,&'\nReading Master Boot Record\n'
	push_pc+1
	call print_str_ROM
	push_pc+1
	call SD.readMBR
	mov A,r0 ; returns r0 = 0 for success, or 1 for error
	cmp A,0x00
	jnz SDcard.error

	mov r0r1,&'\nReading partitions\n'
	push_pc+1
	call print_str_ROM
	push_pc+1
	call SD.readpartitions
	mov A,r0 ; returns r0 = 0 for success, or 1 for error
	cmp A,0x00
	jz SDcard.error

	; Assume partition 0 is valid
	mov A,0x00
	mov SD_CURRENT_PARTITION,A ; use partition 0 for now
	
	push_pc+1
	call SD.readbootsector
	mov A,r0
	cmp A,0x00
	jnz SDcard.error
	
	push_pc+1
	call SD.bootsector_info
	
	push_pc+1
	call SD.get_rootinfo
	
	
	mov r0r1,&'\nSD card OK!\n'
	push_pc+1
	call print_str_ROM
	
	
	pop T
	RET
	
	SDcard.error:
	mov r0r1,&'\nSD ERROR\n'
	push_pc+1
	call print_str_ROM
	
	pop T
	RET
	
SDcard.mount:
	; returns r0 = 0 for success, or 1 for error
	
	SDcard.loop:		
	push_pc+1
	call SD.init

	mov r0r1,SD_CMD0
	push_pc+1
	call SD_sendCMD
	mov A,r0
	cmp A,0x01
	jne SDcard.CMD_failed
	; CMD0 returned 0x01 (success)
	
	mov r0r1,SD_CMD8
	push_pc+1
	call SD_sendCMD
	mov A,r0
	cmp A,0x01 ; might also be 0x05?
	jne SDcard.CMD_failed
	; CMD8 returned 0x01 (success)
	
	mov r5,0x0A		; Try loop ten times
	SD_CMD55_loop:	; doesn't actually loop for now.
	
	mov r0r1,SD_CMD55
	push_pc+1
	call SD_sendCMD
	mov A,r0
	cmp A,0x05
	jne SDcard.CMD55_not_five
	; CMD55 reply is 0x05
	; support older cards
		mov r0r1,SD_CMD1
		push_pc+1
		call SD_sendCMD
		mov A,r0
		cmp A,0x00
		jz SDcard.CMD55_OK
		
		dec r5
		jnz SD_CMD55_loop
		jmp SDcard.CMD_failed
		
	SDcard.CMD55_not_five:
		mov r0r1,SD_CMD41_HCS	; Run ACMD41 with arg 0x40000000 for HCS cards
		push_pc+1
		call SD_sendCMD
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
		inc r3	; to distinguish from other CMD41 call
		mov A,r0
		cmp A,0x00
		jz SDcard.CMD55_OK
		
		dec r5
		jnz SD_CMD55_loop
		jmp SDcard.CMD_failed
		
SDcard.CMD55_OK:
	;mov r0r1,SD_CMD58
	;push_pc+1
	;call SD_sendCMD
	;mov A,r0
	;cmp A,0x00
	;jne SDcard.CMD_failed	
	;CMD58 returned 0x01

	; Turn on SPI
	;mov A,SD_SS
	;or A,0x08	; SPI_EN = 1
	;mov CONTROL_REG,A
	
	; Get second byte 
	; https://github.com/h0m3/SDCore/blob/master/SDCore.cpp
	;mov A,0xFF	; receive byte
	;push_pc+1
	;call SPI.send
	
	;mov A,SPI_PORT	;DEBUG
	;mov r4,A
	;mov r5,0x01
	;push_pc+1
	;call print_hex_ROM
	
	;mov A,SPI_PORT
	;and A,0x40		; SDCore::low_capacity = !(SPDR && 0x40);
	;mov B,A
	;not A		; bug in hardware, actually does not B
	;mov SD_LOW_CAPACITY,A ; card low_capacitiy 
	
	; Get third byte
	;mov A,0xFF	; receive byte
	;push_pc+1
	;call SPI.send
	
	;mov A,SPI_PORT	;DEBUG
	;mov r4,A
	;mov r5,0x01
	;push_pc+1
	;call print_hex_ROM

	;mov A,SPI_PORT
	;and A,0x78			; sets flags
	; Turn off SPI
	;mov A,SD_SS
	;mov CONTROL_REG,A	; SPI_EN = 0, CS not enabled
	;jz SDcard.CMD_failed	; zero is bad, return r1 set as 0x78

	; this is where we would do the final setup stuff
	mov r0r1,SD_CMD16	; Set block size to 512 bytes
	push_pc+1
	call SD_sendCMD
	mov A,r0
	cmp A,0x00
	jnz SDcard.CMD_failed
	
	mov r0r1,SD_CMD59	; Disable CRC checking
	push_pc+1
	call SD_sendCMD
	mov A,r0
	cmp A,0x00
	jnz SDcard.CMD_failed
		
	; if got here then all good!
	mov r0r1,CMD_success
	push_pc+1
	call print_str_ROM
	
	mov r0,0x00		; return r0 = 0 (Success)
	
pop T
RET

SDcard.CMD_failed:
; Could print r0 and r3 codes
; r3 = SD command byte
; r0 = received byte
	mov U,0x0A
	mov U,0x0D	; r1 contains exit code

; DEBUG
	mov r4,r3
	mov r5,0x01
	push_pc+1
	call print_hex_ROM

; DEBUG
	mov r4,r0
	mov r5,0x01
	push_pc+1
	call print_hex_ROM

	mov U,0x0A
	mov U,0x0D

	mov r0,0x01 	; return r0 = 1 (Error)

pop T
RET

CMD_success: dstr 'SD ok!'

SD.readMBR:
	; if low_capacity not 0 then address >>=9 (/512)
	mov r2,0x00
	mov r3,0x00		; 
	mov r4,0x00
	mov r5,0x00		; Master boot sector starts at 0x1be
	
	push_pc+1
	call SD.readblock	; r0 
	mov A,r0
	cmp A,0x00
	jne SD.readMBR.exit	; if r0!=0 then error in reading block, exit and return r0
	
	mov r0,0x01		; return r0 = 1 (ERROR) by default unless passes valid MBR checks
	
	mov A,[0x84fe]	; note, hardcoded
	cmp A,0x55
	jne SD.readMBR.exit
	
	mov A,[0x84ff]
	cmp A,0xAA
	jne SD.readMBR.exit
	
	mov r0,0x00	; if got here then MBR is valid, return r0=0
	
SD.readMBR.exit:
	pop T
	ret

memcpy:	; moves r4 bytes from r0r1 into r2r3
	mov A,[r0r1]
	mov [r2r3],A
	inc r0r1
	inc r2r3
	
	dec r4
	jnz memcpy
	
	pop T
	RET

SD.readpartitions: ; assumes a valid MBR is loaded into memory
	; returns r0=0 for success, r1 = no valid partitions found
	mov r0r1,SD_BLOCK
	mov A,r1
	add A,0xbe
	mov r1,A
	
	mov A,r0
	addc A,0x01
	mov r0,A ;r0r1 = SD_BLOCK + 0x01be. When SD_BLOCK = 0x8300, r0r1 = 0x84be
	
	mov r2,0x00	; 4 partitions
	mov r3,0x00 ; partition valid variable
	
	;mov r4,0x80	; zeropage
	;mov r5,SD_PARTITIONS
	mov r4r5,SD_PARTITIONS
	
	push 0x00	; use stack to record number of valid partitions
	
	SD.readpartitions.loop:	
		mov A,r1
		add A,0x04	; assume r3=0x00, no carry into r2 required
		mov r1,A
		
		mov r3,0x01		; partition valid by default
		
		mov A,[r0r1]	; get partition type
		cmp A,0x04
		je partition.OK
		cmp A,0x06
		je partition.OK
		cmp A,0x0e
		je partition.OK
		cmp A,0x0c		; This is a FAT32 (not FAT16) partition but use for debug purposes for now
		je partition.OK
		; If we got here then partition isn't valid :/
		mov r3,0x00	; invalid partition
		
		jmp partition.nextstep
		
	partition.OK:
		pop A
		inc A
		push A
		
		push r0
		push r1
		mov r0r1,&'Partition '
		push_pc+1
		call print_str_ROM
		
		mov A,r2	; Print partition number
		add A,0x30
		mov U,A
		
		mov r0r1,&': FOUND\n'
		push_pc+1
		call print_str_ROM
		pop r1
		pop r0
	
	partition.nextstep:
		; r3 holds whether we have a valid partition or not
		mov A,r3
		mov [r4r5],A 
		inc r4r5	; next position on zero page
		
		; move to the partition start block, <<9, store and print size
		mov A,r1
		add A,0x04	; add 4 to r0r1 (SD_BLOCK pointer) --> relative offset to partition start in sectors (LBA)
		mov r1,A
		
		mov A,[r0r1]
		mov [r4r5],A
		inc r0r1
		inc r4r5
		
		mov A,[r0r1]
		mov [r4r5],A
		inc r0r1
		inc r4r5
		
		mov A,[r0r1]	;penultimate MSB
		mov [r4r5],A	; save in zero-page partition table
		inc r0r1
		inc r4r5
		
		; don't need the MBS as it will disappear with <<9
		
		mov A,r1
		add A,0x05	; add 5 to r0r1 (SD_BLOCK pointer) --> start of next partition
		mov r1,A
		
		inc r2
		mov A,r2
		cmp A,0x04
		jne SD.readpartitions.loop
	
	pop r0	; put number of valid partitions into r0 for return
	
	pop T
	ret
	
SD.readbootsector:	; needs MBR loaded into memory at 0x8300
	; read in boot sector start from MBR and shift << 9
	
	; Assume partition 0 for now
	;mov r0,0x80
	;mov r1,SD_PARTITIONS
	mov r0r1,SD_PARTITIONS
	mov A,SD_CURRENT_PARTITION
	shl A
	shl A		; A=4*SD_CURRENT PARTITION
	add A,r1
	mov r1,A
	mov A,r0
	addc A,0x00
	mov r0,A	; r0r1 = SD_PARTITIONS + 4*SD_CURRENT_PARTITION
	
	inc r0r1
	mov A,[r0r1]
	mov r5,A	; LSB
	inc r0r1
	mov A,[r0r1]
	mov r4,A
	inc r0r1
	mov A,[r0r1]
	mov r3,A	; MSB
	mov r2,0x00	
	
	push_pc+1
	call SD.readblock	; returns r0
	mov A,r0			; check return code
	cmp A,0x00
	jne SD.readbootsector.exit
	
	;check 0x55AA bootsector signature
	mov r0,0x01		; return r0 = 1 (ERROR) by default unless passes valid MBR checks
	
	mov A,[0x84fe]	; note, hardcoded
	cmp A,0x55
	jne SD.readbootsector.exit
	
	mov A,[0x84ff]
	cmp A,0xAA
	jne SD.readbootsector.exit
	
	mov r0,0x00	; if got here then MBR is valid, return r0=0
SD.readbootsector.exit:	
	pop T
	ret

print_str_n:;prints a string with fixed number of characters
; r0r1 - pointer to string
; r5 - number of characters to print (ignores null-terminated character)
	mov A,[r0r1]
	;cmp A,0x00 ; test for null-terminated string
	;jz print_str_n.end ; change to je for correctness when carry incorporated into logic
	mov U,A ; print character
	inc r0r1; increment pointer
	dec r5
	jz print_str_n.end
	jmp print_str_n
print_str_n.end:
pop T
ret

SD.bootsector_info:	; assumes bootsector is loaded into memory
	mov r0r1,&'\nOEM code:['
	push_pc+1
	call print_str_ROM
	
	mov r0r1,SD_BLOCK
	mov A,r1
	add A,0x03	; 
	mov r1,A
	
	mov r5,0x08
	push_pc+1
	call print_str_n	; i.e. "MSDOS 5.0"

	mov r0r1,&']\nSector size: 0x'
	mov r2r3,SD_BLOCK
	mov r4,0x02	; number of bytes
	mov r5,0x0B	; offset
	push_pc+1
	call SD.print_property
	
	mov r0r1,&'\nSectors per cluster: 0x'
	mov r4,0x01
	push_pc+1
	call SD.print_property
	
	mov r0r1,&'\nReserved sectors: 0x'
	mov r4,0x02
	push_pc+1
	call SD.print_property

	mov r0r1,&'\nNumber of FATs: 0x'
	mov r4,0x01
	push_pc+1
	call SD.print_property
	
	mov r0r1,&'\nFat size sectors: 0x'
	mov r4,0x02
	mov r5,0x05
	push_pc+1
	call SD.print_property

	mov r0r1,&'\nTotal sectors: 0x'
	mov r4,0x04	; Long
	mov r5,0x08
	push_pc+1
	call SD.print_property
	
	mov r0r1,&'\nVolume ID: 0x'
	mov r4,0x04	;Long
	mov r5,0x03
	push_pc+1
	call SD.print_property	
	
	mov r0r1,&'\nVolume label:['
	push_pc+1
	call print_str_ROM
	
	mov r0,r2
	mov r1,r3	; r0r1 = r2r3
	
	mov r5,0x0B		; 11 characters
	push_pc+1
	call print_str_n	; i.e. "NO NAME   "
	
	push r0
	push r1	; r0r1 now points at next entry 
	
	mov r0r1,&']\nFilesystem: ['
	push_pc+1
	call print_str_ROM
	
	pop r1
	pop r0
	mov r5,0x08
	push_pc+1
	call print_str_n	; i.e. "FAT16"
	mov U,']'
	
	pop T
	ret
	
SD.get_rootinfo:	; assumes bootsector is loaded into SD_BLOCK
	mov r2r3,SD_BLOCK
	mov r5,0x0b
	mov r0r1,SD_SECTOR_SIZE
	mov r4,0x02	; 2 bytes of SD_SECTOR_SIZE
	push_pc+1
	call SD.get_property

	mov r4,0x01	; get one byte of SD_SECTORS_PER_CLUSTER
	push_pc+1
	call SD.get_property
	
	mov r4,0x02	; get two bytes of SD_RESERVED_SECTORS
	push_pc+1
	call SD.get_property
	
	mov r4,0x01	; get one byte of SD_NUM_FATS
	push_pc+1
	call SD.get_property
	
	mov r5,0x05	; +5 offset from current position
	mov r4,0x02	; 2 bytes of SD_FAT_SIZE_SECTORS
	push_pc+1
	call SD.get_property
	
	; implement this formula:
	; (start of bootsector partition address + bs.reserved_sectors + bs.fat_size_sectors * bs.number_of_fats) * bs.sector_size
	
	; Check bs.sector is 512 bytes:
	mov r0r1,SD_SECTOR_SIZE
	mov A,[r0r1]
	cmp A,0x02
	jne SD.get_rootinfo.error
	inc r0r1
	mov A,[r0r1]
	cmp A,0x00
	jne SD.get_rootinfo.error
	; if we got here then we can safely <<9 (i.e. 512) in readblock calculation
	
	; Typically:
	; sector_size = 512 (0x0200) - MUST BE TRUE
	; bs.number_of_fats = 2 
	; bs.fat_size_sectors = 239 (0xef)
	; bs.reserved_sectors = 2
	; This is 32-bit maths
	
	; bs.fat_size_sectors (16-bit) * bs.number_of_fats (1 byte) = maximum 24-bit value, likely just 16 bit value
	mov r5,[SD_NUM_FATS] ; i.e. 0x02
	mov r3,SD_FAT_SIZE_SECTORS_MSB
	mov r4,SD_FAT_SIZE_SECTORS_LSB
	mov r0,0x00
	mov r1,0x00
	mov r2,0x00
	mul_loop:	; 16-bit * 8-bit multiply
		mov A,r2	; LSB of r0r1r2
		add A,r4	; add LSB of FAT_SIZE_SECTORS
		mov r2,A
		
		mov A,r1
		addc A,r3	; add MSB of FAT_SIZE_SECTORS to r2, with carry
		mov r1,A
		
		mov A,r0
		addc A,0x00
		mov r0,A
		
		dec r5
		jnz mul_loop
		
	; bs.reserved_sectors (16-bit) + bs.fat_size_sectors * bs.number_of_fats (24-bit number)
	mov r4,SD_RESERVED_SECTORS_MSB
	mov r5,SD_RESERVED_SECTORS_LSB
	mov r3,0x00
	; adding r0r1r2 to r4r5 -> could overflow to r3r0r1r2
	mov A,r2
	add A,r5
	mov r2,A
	
	mov A,r1
	addc A,r4
	mov r1,A
	
	mov A,r0
	addc A,0x00
	mov r0,A
	
	mov A,r3
	addc A,0x00
	mov r3,A
	
	; (start of bootsector partition address + bs.reserved_sectors + bs.fat_size_sectors * bs.number_of_fats) * bs.sector_size
	; add bootsector partition (0) address to r3r0r1r2
	;mov r4,0x80
	;mov r5,SD_PARTITIONS
	mov r4r5,SD_PARTITIONS
	inc r4r5
	mov A,[r4r5]	; LSB
	push A	; LSB on stack - gotta do some messing about because we store the partition address little-endian and need big-endian for the maths
	inc r4r5
	mov A,[r4r5]
	push A	; middle M/LSB on stack
	inc r4r5
	mov A,[r4r5]	; MSB
	pop r4			; middle byte
	pop r5			; LSB
	push A			; push MSB to the stack
	
	mov A,r2
	add A,r5
	mov r2,A
	
	mov A,r1
	addc A,r4
	mov r1,A
	
	pop A			; MSB
	addc A,r0
	mov r0,A
	
	mov A,r3
	addc A,0x00
	mov r3,A
	
	; Finished address
	; r3:r2:r1:r0 (big endian)
	mov r4r5,SD_ROOT_ADDRESSES
	mov A,SD_CURRENT_PARTITION
	shl A
	shl A	; A*4
	mov B,SD_CURRENT_PARTITION
	add A,B ;SD_CURRENT_PARTITION	; 5*A
	
	add A,r5
	mov r5,A
	mov A,r4
	addc A,0x00
	mov r4,A	;r4r5 = SD_ROOT_ADDRESS = 5* SD_CURRENT_PARTITION
	
	mov [r4r5],0x01
	inc r4r5
	mov A,r3
	mov [r4r5],A
	inc r4r5
	mov A,r0
	mov [r4r5],A
	inc r4r5
	mov A,r1
	mov [r4r5],A
	inc r4r5
	mov A,r2
	mov [r4r5],A
	
	; we have r3r0r1r2
	; requires r2r3r4r5
	; therefore:
	mov r5,r2
	mov r4,r1
	mov r2,r3
	mov r3,r0
	push_pc+1
	call SD.readblock
	
SD.get_rootinfo.error:
	mov r0,0x01
SD.get_rootinfo.exit:
	
	pop T
	ret 

SD.get_property:	; not just a straight memcpy, does the offset addition and reverses the order of bytes (SD card is little endian)
; r0r1 pointer to memory to store in
; r2r3 is base address of SD_BLOCK 
; r4 - number of bytes to print
; r5 - offset into r2r3
	; add r4 offset into r2r3 memory block
	mov A,r3
	add A,r5; don't need r5 anymore
	mov r3,A
	mov A,r2
	addc A,0x00
	mov r2,A

	mov r5,r4
	SD.get_property_pushloop:
		mov A,[r2r3]
		push A
		inc r2r3
		dec r4
		jnz SD.get_property_pushloop
	
	SD.get_property_printhexloop:
		pop A	; get MSB first
		mov [r0r1],A
		inc r0r1
		dec r5
		jnz SD.get_property_printhexloop
	pop T
	ret

SD.print_property:
; r0r1 is the string to print
; r2r3 is base address of SD_BLOCK 
; r4 - number of bytes to print
; r5 - offset into r2r3

	; print string with r0r1 pointer
	push_pc+1
	call print_str_ROM	; no longer need r0r1
	
	; add r4 offset into r2r3 memory block
	mov A,r3
	add A,r5; don't need r5 anymore
	mov r3,A
	mov A,r2
	addc A,0x00
	mov r2,A
	
	mov r0,r4 	; r0 is now the number of bytes to print out
	mov r1,r0	; back up into r1 too
	SD.print_property_pushloop:
		mov A,[r2r3]
		push A
		inc r2r3
		dec r0
		jnz SD.print_property_pushloop
	
	SD.print_property_printhexloop:
		pop A	; get MSB first
		mov r4,A
		mov r5,0x00		; no leading '0x', embed in string passed on instead
		push_pc+1
		call print_hex_ROM
		dec r1
		jnz SD.print_property_printhexloop
	pop T
	ret

SD.readblock:
; r2 r3 r4 r5 contains 32-bit address to read (r2 is MSB, r5 is LSB)

; ******************************************
; if need to put as blocks, performs a <<9 of (MSB) r2:r3:r4:r5 (LSB)
	mov A,r5
	shl A
	mov r5,A		; r5 = 2 * [0x84c8]
	
	mov A,r4
	mov B,A
	addc A,B
	mov r4,A		; r4 = 2 * [0x84c7] + carry (r4)
	
	mov A,r3		
	mov B,A
	addc A,B
	mov r3,A		; r3 = 2 * [0x84c6] + carry (r3)
	
	mov r2,r3
	mov r3,r4
	mov r4,r5
	mov r5,0x00
; *****************************************

	mov r0r1,SD_CMD17
	inc r0r1	; put address into CMD17
	mov A,r2
	mov [r0r1],A
	inc r0r1
	mov A,r3
	mov [r0r1],A
	inc r0r1
	mov A,r4
	mov [r0r1],A
	inc r0r1
	mov A,r5
	mov [r0r1],A
	
	mov r0r1,SD_CMD17
	
	push_pc+1
	call SD_sendCMD
	mov A,r0
	cmp A,0x00	
	jnz SD.readblock_exit	; r0 will not be zero on return here

	mov r0,0x01		; set r0, the return value, to be 1 (ERROR) by default
	mov r2,0xff		; read up to 255 times for 0xfe character
	
	; Turn on SPI
	mov A,SD_SS
	or A,0x08	; SPI_EN = 1
	mov CONTROL_REG,A
	
SD.readblock_wait:
	mov A,SPI_PORT
	cmp A,0xFE
	je SD.read_block_FE	; we found start of data block
	
	mov A,0xFF
	push_pc+1
	call SPI.send
	
	dec r2
	jnz SD.readblock_wait
	jmp SD.readblock_exitandOFF	; didn't get 0xFE block character (r0 will be 1 = ERROR)	
	
SD.read_block_FE:
	mov r0r1,SD_BLOCK
	mov r2r3,0x0000
	SD.read_block_FE.loop:	
		mov A,0xFF
		push_pc+1
		call SPI.send
		mov A,SPI_PORT	; get returned byte
		mov [r0r1],A
		
		inc r0r1
		inc r2r3
		mov A,r2
		cmp A,0x02
		jne SD.read_block_FE.loop
	; if we got here then 512 bytes read
	mov A,0xFF	; may not strictly be necessary
	push_pc+1
	call SPI.send
	mov A,0xFF
	push_pc+1
	call SPI.send
	mov r0,0x00		; return r0 = 0 (Success)

SD.readblock_exitandOFF:
	; Turn off SPI
	mov A,SD_SS
	mov CONTROL_REG,A	; SPI_EN = 0, CS not enabled
	
SD.readblock_exit:
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

SD.reset_memory_tables:
	mov r0r1,SD_PARTITIONS
	mov r2,0x10
	reset.partition_clear:
		mov [r0r1],0x00
		inc r0r1
		dec r2
		jnz reset.partition_clear
	
	mov r0r1,SD_ROOT_ADDRESSES
	mov r2,0x14	; 20 bytes
	reset.root.clear:
		mov [r0r1],0x00
		inc r0r1
		dec r2
		jnz reset.root.clear	
		
	pop T
	RET

SD_sendCMD:
; r0r1 - pointer to 6 byte memory location of command
; r0 - return byte with received byte
; r3 - return byte with CMD code

;mov U,0x0A
;mov U,0x0D

push r0
push r1
mov r0r1,&'\nSD CMD '
push_pc+1
call print_str_ROM	; Get rid of newline characters at end of print_str_ROM
pop r1
pop r0

mov r2,0x06
mov A,[r0r1]	; use first byte (SD cmd) as return code error and
and A,0x3f		; extract command number 0b 0 1 cmd number
mov r3,A

mov r4,r3		; DEBUG - print command number
mov r5,0x01
push_pc+1
call print_hex_ROM
mov U,':'

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
	
	mov A,SPI_PORT	;DEBUG
	mov r4,A
	mov r5,0x01
	push_pc+1
	call print_hex_ROM

	mov A,SPI_PORT
	cmp A,0xFF
	jne SD_sendCMD.exit	; found first non-0xFF byte
	
	dec r2
	jnz SD_sendCMD.MISOloop
	
SD_sendCMD.exit:
	mov A,SPI_PORT	; get last received byte (will be 0xFF)
	mov r0,A		; return byte in r0
	
	mov A,SD_SS		; turn off SPI
	mov CONTROL_REG,A	; set slave select = 0, SPI_EN = 0

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