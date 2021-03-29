import serial, time

def movedot(p,v):
    p+=v
    if p>7:
        p=6
        v=-v
    elif p<0:
        p=1
        v=-v
    return (p,v)

def nightrider():
    i=0
    dir=1
    j=1
    dir2=1
    count=0
    while True:
            i,dir = movedot(i,dir)
            count+=1
            if count==14:
                count=0
                j,dir2=movedot(j,dir2)
            a = 1<<i
            b = 1<<j
            time.sleep(0.02)
            ser.write(chr(a|b))

ser=serial.Serial("COM4",38400)
nightrider()

ser.close()
