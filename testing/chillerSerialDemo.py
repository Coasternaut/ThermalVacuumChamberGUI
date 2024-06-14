import serial, time

ser = serial.Serial('/dev/ttyUSB0', 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=1, rtscts=True)

# sets temp
ser.write(bytes('out_sp_00 21.1\r', 'ascii'))

time.sleep(.1)
ser.write(bytes('in_sp_00\r', 'ascii'))

data = float(ser.readline().decode('ascii'))
print(data)