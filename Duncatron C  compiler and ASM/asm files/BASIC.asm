; Some token constants
TOKEN_INT equ 0x01
TOKEN_ASSIGN equ 0x02
TOKEN_LEFT_BRACKET equ 0x03
TOKEN_RIGHT_BRACKET equ 0x04
TOKEN_OPERATOR equ 0x05
TOKEN_STRING equ 0x06
TOKEN_VAR equ 0x07		; NOT USED?
TOKEN_QUOTE equ 0x08
TOKEN_GREATERTHAN equ 0x09
TOKEN_GREATEREQUAL equ 0x0A
TOKEN_LESSTHAN equ 0x0B
TOKEN_LESSEQUAL equ 0x0C
TOKEN_NOTEQUAL equ 0x0D
TOKEN_VARTYPE equ 0x0E
TOKEN_EOF equ 0xFF

; Token data structure:
; 0: Token data type
; 1: Data byte 0
; 2: Data byte 1

Tokenise:
; Input: 
; r0r1 - pointer to SOURCE_STR, zero terminated string
; r2r3 - pointer to token data 
mov r0r1,SOURCE_STR
mov r2r3,TOKEN_DATA
; 
mov r4,0x00	; cursor offset in r0r1 (SOURCE_STR)
Tokenise.mainloop:
	mov A,[r0r1]
	cmp A,0x00
	je Tokenise.end	; found terminating character
	
	cmp A,' '
	jne notwhitespace
		inc r0r1	; ignore whitespace
		inc r4
		jmp Tokenise.mainloop
	
notwhitespace:
	mov r5,r4	; save offset for later
	Tokenise.digitloop: ; check for number token
		mov A,[r0r1] ; in theory A should still be valid?
		cmp A,'0'
		jl skipdigitloop
		cmp A,'9'
		jg skipdigitloop
	
		inc r0r1
		inc r4
		jmp Tokenise.digitloop
	
	skipdigitloop: ; check if we found a number or not
		mov A,r4
		cmp A,r5
		je nonumber
	
		mov [r2r3],TOKEN_INT
		inc r2r3
		mov A,r5
		mov [r2r3],A ; save the number as a bit slice in the source string for now
		inc r2r3
		mov A,r4
		mov [r2r3],A
		inc r2r3
		jmp Tokenise.mainloop
	
	nonumber: ; carry on checking next characters
	mov A,[r0r1]
	cmp A,'('
	jne Tokenise.nextcase1
		mov [r2r3],TOKEN_LEFT_BRACKET
		inc r2r3
		inc r2r3
		inc r2r3
		inc r0r1
		inc r4
		jmp Tokenise.mainloop
	Tokenise.nextcase1:
	mov A,[r0r1]
	cmp A,')'
	jne Tokenise.nextcase2
		mov [r2r3],TOKEN_RIGHT_BRACKET
		inc r2r3
		inc r2r3
		inc r2r3
		inc r0r1
		inc r4
		jmp Tokenise.mainloop
	
	Tokenise.nextcase2:
	mov A,[r0r1]
	cmp A,'+'
	je Tokenise.operator
	cmp A,'-'
	je Tokenise.operator
	cmp A,'*'
	je Tokenise.operator
	cmp A,'/'
	jne Tokenise.nextcase3
	Tokenise.operator:
		mov [r2r3],TOKEN_OPERATOR
		inc r2r3
		mov A,[r0r1]
		mov [r2r3],A
		inc r2r3
		inc r2r3
		inc r0r1
		inc r4
		jmp Tokenise.mainloop
	Tokenise.nextcase3:
	mov A,[r0r1]
	cmp A,'='
	jne Tokenise.nextcase4
		mov [r2r3],TOKEN_ASSIGN
		inc r2r3
		inc r2r3
		inc r2r3
		inc r0r1
		inc r4
		jmp Tokenise.mainloop
	Tokenise.nextcase4:
	mov A,[r0r1]
	cmp A,'%'
	je Tokenise.vartype
	cmp A,'$'
	jne Tokenise.nextcase5
	Tokenise.vartype:
		mov [r2r3],TOKEN_VARTYPE
		inc r2r3
		mov A,[r0r1]
		mov [r2r3],A
		inc r2r3
		inc r2r3
		inc r0r1
		inc r4
		jmp Tokenise.mainloop
		
	Tokenise.nextcase5:
	mov A,[r0r1]
	cmp A,'"'
	jne Tokenise.nextcase6

	mov [r2r3],TOKEN_QUOTE
		inc r2r3
		inc r2r3
		inc r2r3
		
		inc r0r1
		inc r4
		mov r5,r4
		
		string_literal_loop:
		mov A,[r0r1]
		cmp A,'"'
		je string_literal_end
		inc r0r1
		inc r4
		jmp string_literal_loop
		
		string_literal_end:
		mov [r2r3],TOKEN_STRING
		inc r2r3
		mov A,r5
		mov [r2r3],A
		inc r2r3
		mov A,r4
		mov [r2r3],A
		inc r2r3
		
		mov [r2r3],TOKEN_QUOTE
		inc r2r3
		inc r2r3
		inc r2r3
		
		inc r0r1
		inc r4
		jmp Tokenise.mainloop
	Tokenise.nextcase6:
	mov A,[r0r1]
	cmp A,'>'
	jne Tokenise.nextcase7
		inc r0r1
		inc r4
		mov A,[r0r1]	; peek one character ahead
		cmp A,'='	; >=
		jne greater_notequal
			mov [r2r3],TOKEN_GREATEREQUAL
			inc r2r3
			inc r2r3
			inc r2r3
			inc r0r1
			inc r4
			jmp Tokenise.mainloop 
		greater_notequal:
			mov [r2r3],TOKEN_GREATERTHAN
			inc r2r3
			inc r2r3
			inc r2r3
			; we don't have to inc r0r1 or r4 because already need that in peek
			jmp Tokenise.mainloop
	
	Tokenise.nextcase7:
	mov A,[r0r1]
	cmp A,'<'
	jne Tokenise.elsecase
		inc r0r1
		inc r4
		mov A,[r0r1]	; peek one character ahead
		cmp A,'='	; <=
		jne test_notequal
			mov [r2r3],TOKEN_LESSEQUAL
			inc r2r3
			inc r2r3
			inc r2r3
			inc r0r1
			inc r4
			jmp Tokenise.mainloop
		test_notequal:
			mov A,[r0r1]
			cmp A,'>'	; <>
			jne less_notequal
			
			mov [r2r3],TOKEN_NOTEQUAL
			inc r2r3
			inc r2r3
			inc r2r3
			inc r0r1
			inc r4
			jmp Tokenise.mainloop
			
		less_notequal:
			mov [r2r3],TOKEN_LESSTHAN
			inc r2r3
			inc r2r3
			inc r2r3
			; we don't have to inc r0r1 or r4 because already need that in peek
			jmp Tokenise.mainloop
	Tokenise.elsecase:
		mov r5,r4
		
		else_isalpha:
			mov A,[r0r1]
			cmp A,'A'
			jl else_notalpha
			cmp A,'Z'
			jg else_notalpha
			inc r0r1
			inc r4
			jmp else_isalpha
			
		else_notalpha:
			mov A,r4
			cmp A,r5
			je character_error
			
			mov [r2r3],TOKEN_STRING
			inc r2r3
			mov A,r5
			mov [r2r3],A
			inc r2r3
			mov A,r4
			mov [r2r3],A
			inc r2r3
			jmp Tokenise.mainloop
		
		character_error:
		mov A,[r0r1]
		mov U,A
		mov U,'!'
		pop T
		RET
	
Tokenise.end:
	mov [r2r3],TOKEN_EOF
	mov U,':'
	mov U,')'
	pop T
	RET

SOURCE_STR:
dstr 'IF A%<>23*5 THEN B%<C% AND D%<=E$ "hello world!"'
TOKEN_DATA:
