import pandas as pd
import numpy as np
import datetime, sqlite3, random

size = 100000

timestamp = datetime.datetime.now().timestamp()

dbPath = f'testDB_{size}.db'
    
db = sqlite3.connect(dbPath, check_same_thread=False)
db.execute("CREATE TABLE temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG)")
db.execute("CREATE TABLE chiller_log(timestamp, bath_temp, pump_pres, setpoint)")

for i in range(size):
    timestamp += 1
    db.execute("INSERT INTO temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (timestamp,
                            round(random.uniform(0.0, 100.0), 2),
                            round(random.uniform(0.0, 100.0), 2),
                            round(random.uniform(0.0, 100.0), 2),
                            round(random.uniform(0.0, 100.0), 2),
                            round(random.uniform(0.0, 100.0), 2),
                            round(random.uniform(0.0, 100.0), 2),
                            round(random.uniform(0.0, 100.0), 2)))
    db.execute("INSERT INTO chiller_log(timestamp, bath_temp, pump_pres, setpoint) VALUES (?, ?, ?, ?)",
               (timestamp,
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 100.0), 2)))

db.commit()