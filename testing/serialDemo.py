import serial, time

try:
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
except serial.SerialException as e:
    print('no port to open', e)

def getSerialData(portObject):
    try:
        return portObject.readline().decode('ascii')
    except serial.SerialException as e:
         print('Could not read data', e)
         return None


while True:
    data = getSerialData(ser)
    
    if (data):
        tempValueStr = data.split(';')
        tempValueStr.pop()
        
        tempValues = [float(val) for val in tempValueStr]
        print(tempValues)
    else:
        print('no data')
    
    time.sleep(.5)