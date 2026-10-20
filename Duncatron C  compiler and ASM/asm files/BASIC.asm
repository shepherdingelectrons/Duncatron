; Some token constants
TOKEN_INT equ 0x00
TOKEN_ASSIGN equ 0x08
TOKEN_LEFT_BRACKET equ 0x10
TOKEN_RIGHT_BRACKET equ 0x18
TOKEN_OPERATOR_PLUS equ 0x02
TOKEN_OPERATOR_MINUS equ 0x0A
TOKEN_OPERATOR_MUL equ 0x04
TOKEN_OPERATOR_DIV equ 0x0C

TOKEN_STRING equ 0x20
TOKEN_VAR equ 0x28		; NOT USED?
TOKEN_QUOTE equ 0x30

TOKEN_GREATERTHAN equ 0x38
TOKEN_GREATEREQUAL equ 0x40
TOKEN_LESSTHAN equ 0x48
TOKEN_LESSEQUAL equ 0x50
TOKEN_NOTEQUAL equ 0x58
TOKEN_VARTYPE equ 0x60
TOKEN_EOF equ 0xF8

AST_NUMBER equ 0x55
AST_BINARY_OP equ 0xAA
	
; Token data structure:
; 0: Token data type
; 1: Data byte 0
; 2: Data byte 1

doStuff:

	;mov A,0x00
	;mov r5,0x02
	
	;cmp A,r5
	;jle zerolessthanfive
	;mov U,'>'
	;pop t
	;ret
	
	;zerolessthanfive:
	;mov U,'<'
	;pop t
	;ret

	push_pc+1
	call Tokenise
	mov A,r5
	cmp A,0x00
	jnz doStuff.exit
	; Tokenisation okay
	push_pc+1
	call build_AST
	
doStuff.exit:
	pop T
	ret
Tokenise:
; Input: 
; r0r1 - pointer to SOURCE_STR, zero terminated string
; r2r3 - pointer to token data 

;Returns non-zero error in r5 (unexpected character value) if errors, else r5=0
 
mov r0r1,SOURCE_STR
mov r2r3,TOKEN_DATA
; 
mov r4,0x00	; cursor offset in r0r1 (SOURCE_STR)
Tokenise.mainloop:
	mov A,[r0r1]
	cmp A,0x00;
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
	mov r5,TOKEN_OPERATOR_PLUS
	mov A,[r0r1]
	cmp A,'+'
	je Tokenise.operator
	mov r5,TOKEN_OPERATOR_MINUS
	cmp A,'-'
	je Tokenise.operator
	mov r5,TOKEN_OPERATOR_MUL
	cmp A,'*'
	je Tokenise.operator
	mov r5,TOKEN_OPERATOR_DIV
	cmp A,'/'
	jne Tokenise.nextcase3
	Tokenise.operator:
		mov A,r5
		mov [r2r3],A	; r5 holds the operator token
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
		mov r5,A
		mov U,A
		mov U,'!'
		pop T
		RET
	
Tokenise.end:
	mov [r2r3],TOKEN_EOF
	mov U,':'
	mov U,')'
	mov r5,0x00
	pop T
	RET

parse_binary_op:
	; r2 = left - reference/index to AST node
	; r4r5 = memory index into token list
	; r0r1 is global current position into token list
	; needs to return new node index in r2s
	
	; parse_binary_op can call parse_primary and itself so need to ensure any registers are push/popped safely
	; mostly this means r4r5
	
	; get op current_prec and save it somewhere [r4r5]&0x07
	; get op token_value and save it somewhere  [r4r5+1] i.e. '+' or '-' ... can this be encoded into the node_type?
	
	; token format:
	; token_type
	; value
	; data 
	
	; AST_DATA format:
	; node type
	; right node id
	; value
	; left node id
	
	push r2	; r2 = left don't need this until the end of the function
	
	mov A,[r4r5]
	and A,0x07
	push A		; current precedence on stack
	;mov r3,A		
	
	inc r4r5
	mov A,[r4r5]	; token value
	push A ; token_value
	
	push_pc+1
	call parse_primary	; this may change r4, r2 (and r5)
	; right is in r2 in return from parse_primary = right
	pop r4			; restore r4 = token_value
	pop r5			; restore r5 = current prec
	
	push r4 		; push token_value onto stack
	
	parse_binary_op.enter_while:	
		mov A,[r0r1]	; get precedence at cursor position
		and A,0x07
		cmp A,r5		; 
		jle parse_binary_op.exit_while
		
		push r4	
		push r5
	
		mov r4,r0
		mov r5,r1	; r4r5 = next_op
		inc r0r1
		inc r0r1
		inc r0r1 	; consume token, cursor+=1
		
		;set up call to parse_binary_op
		; r2 is passed on and already right node, will be replaced in return.
		; r4 and 
		push_pc+1
		call parse_binary_op
		; r2 returns the right node id
		pop r5
		pop r4
		jmp parse_binary_op.enter_while
	
	parse_binary_op.exit_while:
	; got here, need:
	; r2 = right node id
	; r3 = global index into AST_DATA
	; 
	mov r4r5,AST_NODES
	mov A,r3		; index into AST_NODES
	shl A
	shl A
	add A,r5
	mov r5,A
	mov A,r4
	addc A,0x00
	mov r4,A 	; r4r5 = AST_NODES + 4*r3
	
	mov [r4r5],AST_BINARY_OP
	inc r4r5
	mov A,r2		; r2 currently holds 'right' node id
	mov [r4r5],A	; note, we changed the node format to have right node here (for reasons of register availability..)
	inc r4r5
	pop r2			; token value (was r4)
	mov A,r2
	mov [r4r5],A
	inc r4r5
	pop r2			; left node value (passed on as r2 into function originally)
	mov A,r2
	mov [r4r5],A
	
	mov r2,r3
	inc r3
	
	pop T
	ret 
parse_primary:
	; r0r1 is a pointer to a position in TOKEN_DATA (basically self.cursor)
	; takes no parameters
	; RETURNS: new node id in r2
	
	mov A,[r0r1]
	cmp A,TOKEN_LEFT_BRACKET
	jne parse_primary.check_number
		; found a left bracket
		inc r0r1
		inc r0r1
		inc r0r1	; consume token
		push_pc+1
		call parse_expression ; r2 holds node ID
		
		mov A,[r0r1]
		cmp A,TOKEN_RIGHT_BRACKET
		jne parse_primary.error		
		; found ')'
		inc r0r1
		inc r0r1
		inc r0r1 	; consume token
		; r2 still holds the node ID, return
		pop T
		ret
		
	parse_primary.check_number:
	mov A,[r0r1]
	cmp A,TOKEN_INT
	jne parse_primary.error
		; found a number!
		; this is where we would go and get the actual value of the number
		; for now value can be first data byte (token_value)
		
		
		mov r4r5,AST_NODES ; I THINK I can use r4r5, it is used as a paramter to parse_binary_op but should be okay
		mov A,r3	; use r3 as a pointer offset into AST_NODES
		shl A
		shl A	; A = r3 * 4
		add A,r5
		mov r5,A
		mov A,r4
		addc A,0x00
		mov r4,A
		
		mov [r4r5],AST_NUMBER
		inc r4r5
		
		inc r0r1
		mov A,[r0r1]	; this is the token_value for now
		;mov A,r2			; r2 is the token value for now
		mov [r4r5],A		; set value, no left or right nodes (in future left and right could form a 16-bit address/number?)
		inc r4r5
		inc r0r1
		mov A,[r0r1]
		mov [r4r5],A
		inc r0r1		; consume token
		
		mov r2,r3	; r2 is returns
		inc r3		; r3 tracks the number of AST nodes
		pop T
		ret
	
	parse_primary.error:
	    mov U,'£'
		add A,0x30 ;'0'
		mov U,A
		mov U,'!'
		mov r2,0xff
		pop T
		ret
	
parse_expression:
; takes no parameters, returns tree node ID in r2
	push_pc+1
	call parse_primary	; returns an index in AST_NODES in r2
	push r2 	; left - push it onto stack to preserve because function is recursive
	
	parse_expression.while:
		mov A,[r0r1]	; token_type
		and A,0x07
		jz parse_expression.exit_while	; check precedence position
		
		mov r4,r0
		mov r5,r1	; r4r5 = r0r1 = op, to pass onto parse_binary_op 

		inc r0r1
		inc r0r1
		inc r0r1	; move to next token record
		
		pop r2 		; get left, index into AST array to pass onto parse_binary_op. 
		push_pc+1
		call parse_binary_op	; left, op
		push r2		; returns an index in AST_NODES in r2
		
		jmp parse_expression.while
		
	parse_expression.exit_while:
	pop r2	; left = r2 is 'returned'
	
	pop T
	ret
	
build_AST:
	mov r0r1,TOKEN_DATA	;self.cursor = 0
	mov r3,0x00	; size of AST_NODES
	push_pc+1
	call parse_expression
	; r2 holds the parent node ID
	mov A,'0'
	add A,r2
	mov U,A
	
	pop T
	ret
; need to add some kind of error handling for AST tree building

SOURCE_STR:
dstr '5/((2+3)*(34-4))'
;IF A%<>23*5 THEN B%<C% AND D%<=E$ "hello world!"'
TOKEN_DATA:
db [255]	; bit of padding
AST_NODES:
; current data structure:
; NODE_TYPE,value (ie for binary_op), left, right.
dstr 'AST'

; epFepnbpn2#0%bp£4!4#0%0bpn4#0%0%0%B{!/
