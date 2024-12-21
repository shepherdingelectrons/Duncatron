import serial

ser = serial.Serial('COM4',38400,timeout=0)

while True:
    s = ser.read()

    for b in s:
        print(b,chr(b))
        
