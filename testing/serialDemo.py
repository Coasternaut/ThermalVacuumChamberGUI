import serial

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

while True:
    data = ser.readline().decode('ascii')
    
    tempValueStr = data.split(';')
    tempValueStr.pop()
    
    tempValues = [float(val) for val in tempValueStr]
    print(tempValues)