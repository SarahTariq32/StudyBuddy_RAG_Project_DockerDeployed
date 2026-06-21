import sqlite3

conn = sqlite3.connect("app.db")
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in app.db:", [r[0] for r in rows])
conn.close()
