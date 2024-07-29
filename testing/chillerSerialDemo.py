import serial, serial.tools.list_ports, time

def getDevicePath(serialNumber):
    for port in serial.tools.list_ports.comports():
        if port.serial_number == serialNumber:
            return port.device
    
    return None

ser = serial.Serial(getDevicePath('AL066BK6'), 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=1, rtscts=True)

ser.reset_input_buffer()

clock = time.time()
ser.write(bytes('in_sp_00\r', 'ascii'))
print("Write time: ", time.time() - clock)

clock = time.time()
data = ser.read_until(b'\r')
print("Read time: ", time.time() - clock)

print("Data: ", data, ' Length: ', len(data))