-- AI 新闻数据库 Schema
-- 仅包含 3 张表：source_crawl_configs / primary_sources / importance_ai

CREATE TABLE IF NOT EXISTS source_crawl_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url_norm TEXT NOT NULL UNIQUE,
  name TEXT,
  source_type TEXT DEFAULT 'html',
  is_flash INTEGER DEFAULT 0,
  content_extract TEXT,
  publish_time_pattern TEXT,
  list_config TEXT,
  checked INTEGER DEFAULT 0,
  crawl_order INTEGER DEFAULT 100,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS primary_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT NOT NULL,
  title TEXT,
  url TEXT NOT NULL UNIQUE,
  summary TEXT,
  publish_time TEXT,
  content TEXT,
  content_length INTEGER DEFAULT 0,
  batch_id INTEGER NOT NULL DEFAULT 0,
  is_useful INTEGER DEFAULT 0,
  status TEXT DEFAULT 'new' CHECK(status IN ('new','read','scored','pushed','error')),
  fetched_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS importance_ai (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_id INTEGER NOT NULL,
  source_name TEXT NOT NULL,
  title TEXT,
  url TEXT,
  publish_time TEXT,
  summary TEXT,
  score INTEGER DEFAULT 0,
  tech_novelty INTEGER,
  monetization TEXT,
  domains TEXT,
  highlights TEXT,
  reason TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);