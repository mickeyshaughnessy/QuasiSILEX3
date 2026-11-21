; 10 mm square from the current work origin.
; S300 is 30% when $30 is 1000. Set Zero here before running.
G21
G90
G0 X0 Y0
M3 S0
G1 F800 X10 Y0 S300
G1 X10 Y10
G1 X0 Y10
G1 X0 Y0
M5
G0 X0 Y0
