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
RET


