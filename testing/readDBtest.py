import sqlite3, time

dbPath = 'test_data/logSyncTime2024-07-09--10-12-15.db'

db = sqlite3.connect(dbPath, check_same_thread=False)
cur = db.cursor()

maxTime = time.time() + 100

#cur.row_factory = lambda cursor, row: row[0]

cur.execute(f"SELECT timestamp, tempA FROM temp_log")
data = cur.fetchall()

print([d[0] for d in data])
print([d[1] for d in data])