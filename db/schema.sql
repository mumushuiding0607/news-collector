-- 一手新闻主表
CREATE TABLE IF NOT EXISTS primary_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  subtitle TEXT,
  publish_time TEXT,
  content TEXT,
  content_length INTEGER DEFAULT 0,
  status TEXT DEFAULT 'new',
  fetched_at TEXT DEFAULT (datetime('now','localtime')),
  content_fetched_at TEXT
);

-- 采集日志表
CREATE TABLE IF NOT EXISTS collect_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT,
  url TEXT,
  status TEXT CHECK(status IN ('new','fetched','pushed','error')),
  note TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);