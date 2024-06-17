import sqlite3, time

dbPath = 'testDB_100.db'

db = sqlite3.connect(dbPath, check_same_thread=False)
cur = db.cursor()

maxTime = time.time() + 100

cur.row_factory = lambda cursor, row: row[0]

cur.execute("SELECT timestamp FROM temp_log WHERE timestamp < ?", (maxTime,))
timestamps = cur.fetchall()

cur.execute("SELECT tempA FROM temp_log WHERE timestamp < ?", (maxTime,))
temps = cur.fetchall()

print(timestamps)
print(temps)