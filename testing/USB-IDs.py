import serial

import serial.serialutil
import serial.tools
import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
serialPaths = []
for p in ports:
    print(p.device, p.vid, p.pid, p.hwid, p.product, p.serial_number)

# RS232 SN: AL066BK6
# RS485 SN: B001YA5C
# Arduino SN: D12A5A1851544B5933202020FF080B15