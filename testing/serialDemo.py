import serial, time

import serial.serialutil
import serial.tools
import serial.tools.list_ports

def getOpenPaths():
    ports = serial.tools.list_ports.comports()
    serialPaths = []
    for p in ports:
        serialPaths.append(p.device)
    return serialPaths

def getArduinoPath(paths):
    for path in paths:
        if path[:-1] == '/dev/ttyACM':
            return path
    return None

def getDevicePath(serialNumber):
    for port in serial.tools.list_ports.comports():
        if port.serial_number == serialNumber:
            return port.device
        
    return None


try:
    ser = serial.Serial(getDevicePath('D12A5A1851544B5933202020FF080B15'), 9600, timeout=1)
    
except serial.SerialException as e:
    print('no port to open', e)

def getSerialData(portObject):
    try:
        return portObject.readline().decode('ascii')
    except (serial.serialutil.PortNotOpenError, serial.serialutil.SerialException)  as e:
        print('error: ', e)
        paths = getOpenPaths()
        print(paths)
        try:
                portObject.close()
                ser.port = getArduinoPath(paths)
                portObject.open()
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