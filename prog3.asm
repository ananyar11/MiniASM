; Program 3: Countdown loop (tests backward jump and JZ)
; Expected: 1003 1101 1200 3001 5002 7007 6003 0000
       MOV R0, 3
       MOV R1, 1
       MOV R2, 0
LOOP:  SUB R0, R1
       CMP R0, R2
       JZ DONE
       JMP LOOP
DONE:  HALT
