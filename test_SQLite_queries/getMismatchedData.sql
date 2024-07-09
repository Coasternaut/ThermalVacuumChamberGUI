-- SQLite
-- SELECT * FROM temp_log t LEFT JOIN chiller_log c ON t.timestamp = c.timestamp UNION SELECT * FROM chiller_log LEFT JOIN temp_log ON chiller_log.timestamp = temp_log.timestamp
SELECT * FROM temp_log UNION SELECT * FROM chiller_log