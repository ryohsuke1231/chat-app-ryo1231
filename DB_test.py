import sqlite3
with sqlite3.connect("chat.db") as conn:
  rows = conn.execute("SELECT * FROM users").fetchall()
  for row in rows:
      print(row)
