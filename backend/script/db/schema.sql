-- 新闻采集系统数据库Schema
-- 维护者：schema.sql 是唯一的表结构定义源

-- ============================================
-- 一手新闻主表
-- ============================================
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
  is_useful INTEGER DEFAULT 0,  -- 0=未评估, 1=有用, -1=无用
  status TEXT DEFAULT 'new' CHECK(status IN ('new','read','scored','pushed','error')),
  fetched_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================
-- 采集日志表
-- ============================================
CREATE TABLE IF NOT EXISTS collect_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT,
  url TEXT,
  status TEXT CHECK(status IN ('new','fetched','pushed','error')),
  note TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================
-- 新闻评分表（事件评估框架）
-- ============================================
CREATE TABLE IF NOT EXISTS importance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_id INTEGER NOT NULL,
  batch_id INTEGER NOT NULL DEFAULT 0,
  source_name TEXT NOT NULL,
  title TEXT,
  url TEXT,
  publish_time TEXT,
  summary TEXT,
  related_sectors TEXT,
  importance_score INTEGER DEFAULT 0,
  reason TEXT,
  direction TEXT,
  intensity INTEGER,
  expected_change TEXT,
  duration TEXT,
  expectation_level TEXT,
  market_mode TEXT,
  publish_sector_values TEXT,
  current_sector_values TEXT,
  current_sector_change_rates TEXT,
  max_sector_rise REAL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 索引：news_id 唯一去重（同一新闻只保留一次评分，避免并发跑分/历史残留导致重复）
CREATE UNIQUE INDEX IF NOT EXISTS idx_importance_news_id ON importance(news_id);
CREATE INDEX IF NOT EXISTS idx_importance_batch_score ON importance(batch_id, importance_score);
CREATE INDEX IF NOT EXISTS idx_importance_created_at ON importance(created_at);

-- ============================================
-- 板块指数记录表
-- ============================================
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

-- ============================================
-- 板块表（用于归一化匹配）
-- ============================================
CREATE TABLE IF NOT EXISTS sectors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  name_pinyin_initial TEXT,
  name_pinyin_full TEXT,
  keywords TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================
-- FTS5全文索引（板块搜索）
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS sectors_fts USING fts5(
  name,
  keywords,
  content='sectors',
  content_rowid='id'
);

-- ============================================
-- FTS5同步触发器
-- ============================================
-- INSERT 触发器
CREATE TRIGGER IF NOT EXISTS sectors_ai AFTER INSERT ON sectors BEGIN
  INSERT INTO sectors_fts(rowid, name, keywords) VALUES (new.id, new.name, new.keywords);
END;

-- DELETE 触发器
CREATE TRIGGER IF NOT EXISTS sectors_ad AFTER DELETE ON sectors BEGIN
  INSERT INTO sectors_fts(sectors_fts, rowid, name, keywords) VALUES ('delete', old.id, old.name, old.keywords);
END;

-- UPDATE 触发器
CREATE TRIGGER IF NOT EXISTS sectors_au AFTER UPDATE ON sectors BEGIN
  INSERT INTO sectors_fts(sectors_fts, rowid, name, keywords) VALUES ('delete', old.id, old.name, old.keywords);
  INSERT INTO sectors_fts(rowid, name, keywords) VALUES (new.id, new.name, new.keywords);
END;

-- ============================================
-- 新闻-核心标的关联表（事件驱动的标的发现）
-- ============================================
CREATE TABLE IF NOT EXISTS news_stocks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  importance_id INTEGER NOT NULL,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  tier TEXT,
  chain_link TEXT,
  four_dims TEXT,
  moat TEXT,
  news_related TEXT,
  d1 TEXT, -- 发布当天收盘涨跌幅
  d2 TEXT, -- 发布后第1天涨跌幅
  d3 TEXT, -- 发布后第2天涨跌幅
  created_at TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (importance_id) REFERENCES importance(id)
);

-- 索引：importance_id 去重 + 高效查询
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_stocks_importance_code ON news_stocks(importance_id, code);
CREATE INDEX IF NOT EXISTS idx_news_stocks_importance_id ON news_stocks(importance_id);


-- ============================================
-- 用户账号表
-- ============================================
CREATE TABLE IF NOT EXISTS auth_users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT UNIQUE,
  password_hash TEXT,
  nickname TEXT,
  avatar_url TEXT,
  email TEXT UNIQUE,
  subscription_level TEXT DEFAULT 'free' CHECK(subscription_level IN ('free','pro','premium')),
  subscription_expire_at TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 验证码表
CREATE TABLE IF NOT EXISTS auth_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT NOT NULL,
  code TEXT NOT NULL,
  expire_at TEXT NOT NULL,
  used INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 订阅记录表
CREATE TABLE IF NOT EXISTS subscription_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  level TEXT NOT NULL CHECK(level IN ('pro','premium')),
  price REAL NOT NULL,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  status TEXT DEFAULT 'active' CHECK(status IN ('active','expired','cancelled','pending_confirm','proof_requested')),
  note TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (user_id) REFERENCES auth_users(id)
);

-- 意见反馈表
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  type TEXT CHECK(type IN ('bug','suggestion','content','other')),
  content TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (user_id) REFERENCES auth_users(id)
);

-- 评论表
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  processed INTEGER DEFAULT 0,  -- 0=未处理, 1=已处理
  created_at TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (news_id) REFERENCES importance(id),
  FOREIGN KEY (user_id) REFERENCES auth_users(id)
);

-- 登录尝试次数表（频率限制）
CREATE TABLE IF NOT EXISTS login_attempts (
  phone TEXT PRIMARY KEY,
  attempt_count INTEGER DEFAULT 0,
  locked_until TEXT
);

-- 密码重置验证码表
CREATE TABLE IF NOT EXISTS reset_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expire_at TEXT NOT NULL,
  used INTEGER DEFAULT 0
);

-- 邮箱注册验证码表
CREATE TABLE IF NOT EXISTS email_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expire_at TEXT NOT NULL,
  used INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================
-- 订单表（微信支付）
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_no TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  level TEXT NOT NULL CHECK(level IN ('pro','premium')),
  amount REAL NOT NULL,
  pay_method TEXT DEFAULT 'wechat' CHECK(pay_method IN ('mock','personal','wechat')),
  status TEXT DEFAULT 'pending' CHECK(status IN ('pending','paid','cancelled','expired')),
  trade_no TEXT,
  wechat_prepay_id TEXT,
  wechat_code_url TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  updated_at TEXT DEFAULT (datetime('now','localtime')),
  expire_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES auth_users(id)
);

-- ============================================
-- 数据源管理表
-- ============================================

-- 数据源抓取配置表（按规范化 URL 唯一索引）
CREATE TABLE IF NOT EXISTS source_crawl_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url_norm TEXT NOT NULL UNIQUE,               -- 规范化 URL（唯一索引）
  name TEXT,                                   -- 数据源名称
  source_type TEXT DEFAULT 'html', -- 加载方式：html|api|ajax
  is_flash INTEGER DEFAULT 0,                 -- 是否为 flash 数据源：0=否，1=是
  content_extract TEXT,                        -- 内容提取正则
  publish_time_pattern TEXT,                   -- 发布时间提取正则
  list_config TEXT,                            -- 新闻列表获取配置（JSON）
  checked INTEGER DEFAULT 0,                   -- 是否已检查确认：0=未检查，1=已确认
  crawl_order INTEGER DEFAULT 100,             -- 抓取优先级，越小越先抓取
  created_at TEXT DEFAULT (datetime('now','localtime')),
  updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 异动消息表（保存有数据源的异动消息）
CREATE TABLE IF NOT EXISTS anomaly_news (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,                           -- 异动标题
  url TEXT,                                      -- 文章链接
  publish_time TEXT,                             -- 发布时间
  source_name TEXT NOT NULL,                     -- 数据源名称
  content TEXT,                                   -- 文章正文
  content_length INTEGER DEFAULT 0,              -- 正文长度
  content_crawled_at TEXT,                       -- 正文采集时间
  processed INTEGER DEFAULT 0,                    -- 是否处理：0未处理，1已处理
  created_at TEXT                                -- 创建时间（代码中设置）
);

-- 索引：anomaly_news 按 source_name 和 publish_time 筛选
CREATE INDEX IF NOT EXISTS idx_anomaly_source ON anomaly_news(source_name);
CREATE INDEX IF NOT EXISTS idx_anomaly_time ON anomaly_news(publish_time);

-- ============================================
-- 待确认数据源表
-- ============================================
-- ============================================
-- 简报表
-- ============================================
CREATE TABLE IF NOT EXISTS summary (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,                            -- 简报日期
  type TEXT DEFAULT '异动简报',                   -- 简报类型
  content TEXT,                                  -- 简报内容（JSON）
  created_at TEXT DEFAULT (datetime('now','localtime')),
  UNIQUE(date, type)
);

-- ============================================
-- 用户反馈汇总表
-- ============================================
CREATE TABLE IF NOT EXISTS user_feedback_summary (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_id INTEGER NOT NULL,
  feedback_content TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);