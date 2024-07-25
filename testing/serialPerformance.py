import serial, serial.tools.list_ports, time

def getDevicePath(serialNumber):
    for port in serial.tools.list_ports.comports():
        if port.serial_number == serialNumber:
            return port.device
    
    return None

ser = serial.Serial(getDevicePath('B001YA5C'), 19200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)

ser.reset_input_buffer()

clock = time.time()
ser.write(bytes('#01RD\r', 'ascii'))
print("Write time: ", time.time() - clock)

clock = time.time()
data = ser.read_until(b'\r')
print("Read time: ", time.time() - clock)

print("Data: ", data)