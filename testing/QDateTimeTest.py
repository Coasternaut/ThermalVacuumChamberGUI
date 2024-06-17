from PyQt6.QtCore import QDateTime
import datetime

timestamp = datetime.datetime.now().timestamp()
timestampInt = round(timestamp)

dt = QDateTime(0,0,0,0,0)
print(dt)

dt.setSecsSinceEpoch(timestampInt)
print(dt)