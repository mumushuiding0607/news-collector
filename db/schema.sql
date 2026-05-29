-- 一手新闻主表
CREATE TABLE IF NOT EXISTS primary_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT NOT NULL,
  title TEXT,
  url TEXT NOT NULL UNIQUE,
  subtitle TEXT,
  publish_time TEXT,
  content TEXT,
  content_length INTEGER DEFAULT 0,
  batch_id INTEGER NOT NULL DEFAULT 0,
  is_useful INTEGER DEFAULT 0,  -- 0=未评估, 1=有用, -1=无用
  status TEXT DEFAULT 'new' CHECK(status IN ('new','read','scored','pushed','error')),
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

-- 新闻评分表（enhanced with event evaluation framework）
CREATE TABLE IF NOT EXISTS importance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_id INTEGER NOT NULL,
  source_name TEXT NOT NULL,
  title TEXT,
  url TEXT,
  publish_time TEXT,
  summary TEXT,
  related_sectors TEXT,
  importance_score INTEGER DEFAULT 0,
  reason TEXT,
  -- 事件评估框架扩展字段
  direction TEXT,
  intensity INTEGER,
  expected_change TEXT,
  duration TEXT,
  expectation_level TEXT,
  market_mode TEXT,
  -- 元数据
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 板块指数记录表
CREATE TABLE IF NOT EXISTS sector_indices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  importance_id INTEGER NOT NULL,
  sector_code TEXT,
  sector_name TEXT,
  change_rate TEXT,
  turnover TEXT,
  volume TEXT,
  amount TEXT,
  dde_net_amount TEXT,
  query_time TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (importance_id) REFERENCES importance(id)
);

-- 板块表（用于归一化匹配）
CREATE TABLE IF NOT EXISTS sectors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  name_pinyin_initial TEXT,
  name_pinyin_full TEXT,
  keywords TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- FTS5全文索引（板块搜索）
CREATE VIRTUAL TABLE IF NOT EXISTS sectors_fts USING fts5(
  name, keywords,
  content='sectors',
  content_rowid='id'
);