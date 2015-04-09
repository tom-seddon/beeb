;;; beebasm-mode
;;
;; For use with BeebAsm - http://www.retrosoftware.co.uk/wiki/index.php/BeebAsm

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defgroup beebasm nil
  "Major mode for editing 6502 code for use with BeebAsm"
  :prefix "beebasm-"
  :group 'languages)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defun beebasm--caseify-string (x)
  `(sequence ,@(mapcar (lambda (c)
			 `(any ,(make-string 1 c) ,(make-string 1 (downcase c))))
		       x)))
  
;; (defun beebasm--caseify-list (xs)
;;   `(or ,@(mapcar 'beebasm--caseify-string xs)))

(defvar beebasm-font-lock-keywords
  (let ((builtins '("LO" "HI" "SQR" "SIN" "COS" "TAN" "ASN" "ACS"
		    "ATN" "RAD" "DEG" "INT" "ABS" "SGN" "RND" "RND"
		    "NOT" "LOG" "LN" "EXP" "PI" "FALSE" "TRUE"))
	(instructions (mapcar 'beebasm--caseify-string
			      '("ADC" "AND" "ASL" "BCC" "BCS" "BEQ" "BIT" "BMI"
				"BNE" "BPL" "BRK" "BVC" "BVS" "CLC" "CLD" "CLI"
				"CLV" "CMP" "CPX" "CPY" "DEC" "DEX" "DEY" "EOR"
				"INC" "INX" "INY" "JMP" "JSR" "LDA" "LDX" "LDY"
				"LSR" "NOP" "ORA" "PHA" "PHP" "PLA" "PLP" "ROL"
				"ROR" "RTI" "RTS" "SBC" "SEC" "SED" "SEI" "STA"
				"STX" "STY" "TAX" "TAY" "TSX" "TXA" "TXS" "TYA")))
	(stuff '("ORG" "CPU" "SKIP" "SKIPTO" "ALIGN" "INCLUDE" "INCBIN"
		 "EQUB" "EQUW" "EQUD" "EQUS" "MAPCHAR" "GUARD" "CLEAR"
		 "SAVE" "PRINT" "ERROR" "FOR" "IF" "ELIF" "ELSE" "ENDIF"
		 "PUTFILE" "PUTBASIC" "MACRO")))
    `(
      (,(rx (any ";\\")
	    (zero-or-more any)
	    eol) . font-lock-comment-face)

      (,(eval `(rx symbol-start
		   (or ,@builtins))) . font-lock-builtin-face)

      (,(eval `(rx symbol-start
		   (or ,@instructions))) . font-lock-keyword-face)

      (,(eval `(rx symbol-start
		   (or ,@stuff)
		   symbol-end)) . font-lock-preprocessor-face))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define-derived-mode
    beebasm-mode
    prog-mode
    "beebasm"
  "Mode for editing BeebAsm 6502 source."

  ;;
  ;; comment
  ;;
  (make-local-variable 'comment-start)
  (setq comment-start "; ")

  ;; 
  ;; font lock
  ;; 
  (make-local-variable 'font-lock-defaults)
  (setq font-lock-defaults '(beebasm-font-lock-keywords nil t))

  ;;
  ;; syntax table
  ;;
  (modify-syntax-entry 59 "<" beebasm-mode-syntax-table)
  (modify-syntax-entry ?\\ "<" beebasm-mode-syntax-table)
  (modify-syntax-entry ?\n ">" beebasm-mode-syntax-table)

  (loop for c in `(?+ ?- ?* ?/ ?< ?> ?^ ?( ?) ?[ ?] ?= ?!)
	do
	(modify-syntax-entry c "." beebasm-mode-syntax-table))

  ;; . and % are symbol constituent chars
  (modify-syntax-entry ?. "_" beebasm-mode-syntax-table)
  (modify-syntax-entry ?% "_" beebasm-mode-syntax-table)

  ;;
  ;; compilation
  ;;
  (setq compilation-error-regexp-alist
	`((,(rx line-start
		(0+ space)
		(group (1+ any))
		":"
		(group (1+ digit))
		": ")			; the space is to stop it
					; finding the "Compilation
					; started at..." line.
	   1
	   2)))

  ;;
  ;; imenu
  ;;
  (setq imenu-generic-expression
	`(("Symbol"
	   ,(rx bol
		(group (sequence "."
				 (any alphabetic "_")
				 (zero-or-more (any alphanumeric "_")))))
	   1)
	  ("Macro"
	   ,(rx bol
		(zero-or-more space)
		"MACRO"
		(one-or-more space)
		(any alphabetic "_")
		(zero-or-more (any alphanumeric "_")))))))
		
  

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(provide 'beebasm-mode)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
