; Program 2: Forward jump (tests Pass 1 and Pass 2)
; Expected: 1001 6003 1063 0000
START: MOV R0, 1
       JMP END
       MOV R0, 99
END:   HALT
