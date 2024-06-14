import serial

ser = serial.Serial('/dev/cu.usbserial-AL066BK6', 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=1, rtscts=True)

while True:
    ser.write('in_pv_00'.encode('utf-8'))
    data = ser.readline().decode('ascii')

    print(data)