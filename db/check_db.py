import sqlite3
conn = sqlite3.connect(r'E:\Workspaces\MoltBot\新闻采集和分析\db\primary.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print([r[0] for r in cur.fetchall()])
conn.close()