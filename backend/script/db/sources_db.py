"""
sources_db.py - 数据源数据库访问层

所有 sources / source_crawl_configs 的 CRUD 必须通过此模块。
"""
from __future__ import annotations
import json
from script.db import get_conn, put_conn
from script.common.urlutil import normalize_url
from script.common.jsonutil import parse_json_field


__all__ = [
    "list_sources",
    "get_source_by_id",
    "get_source_by_name",
    "get_source_by_url",
    "normalize_url",
    "normalize_url_for_db",
    "source_exists_by_url_and_owner",
    "add_source",
    "update_source",
    "delete_source",
    "get_crawl_config",
    "get_crawl_config_by_url",
    "find_learned_config_by_name",
    "get_crawl_config_by_domain",
    "extract_domain",
    "upsert_crawl_config",
    "ensure_crawl_config",
    "list_sources_with_configs",
    "list_user_sources",
    "delete_crawl_config",
    "get_content_extract_by_name",
    "get_publish_time_extract_by_name",
    "get_content_extract_config",
]


# ============ sources CRUD ============


def list_sources(owner_id: int | None = None, include_inactive: bool = False):
    """返回 sources 列表，owner_id=None 返回所有（管理员）"""
    conn = get_conn()
    try:
        conditions = ["1=1"]
        params = []
        if owner_id is not None:
            conditions.append("(owner_id IS NULL OR owner_id = ?)")
            params.append(owner_id)
        if not include_inactive:
            conditions.append("is_active = 1")
        where = " AND ".join(conditions)
        rows = _dict(conn,
            f"SELECT id, name, url_norm, owner_id, is_active, is_flash, created_at "
            f"FROM sources WHERE {where} ORDER BY id",
            params,
        )
        for r in rows:
            r["url"] = r["url_norm"] or r.get("url", "")
        return rows
    finally:
        put_conn(conn)


def get_source_by_id(source_id: int):
    conn = get_conn()
    try:
        rows = _dict(conn, "SELECT * FROM sources WHERE id = ?", (source_id,))
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def get_source_by_name(name: str):
    conn = get_conn()
    try:
        rows = _dict(conn, "SELECT * FROM sources WHERE name = ?", (name,))
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def normalize_url_for_db(url: str) -> str:
    """URL 规范化（内存中使用，不存入数据库）：统一 http/https，去末尾 /"""
    if not url:
        return ""
    return normalize_url(url)


def source_exists_by_url_and_owner(url: str, owner_id: int | None) -> bool:
    """检查同一用户是否已添加过此数据源 URL"""
    conn = get_conn()
    try:
        norm = normalize_url_for_db(url)
        row = conn.execute(
            "SELECT id FROM sources WHERE url_norm = ? AND owner_id IS NOT DISTINCT FROM ?",
            (norm, owner_id),
        ).fetchone()
        return row is not None
    finally:
        put_conn(conn)


def get_source_by_url(url: str):
    """通过规范化后的 URL 查找数据源"""
    norm_url = normalize_url(url)
    conn = get_conn()
    try:
        rows = _dict(conn, "SELECT * FROM sources WHERE url_norm = ?", (norm_url,))
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def add_source(name: str, url: str, owner_id: int | None = None,
               is_flash: bool = False) -> int:
    """添加数据源，返回 id"""
    conn = get_conn()
    try:
        norm = normalize_url_for_db(url)
        cursor = conn.execute(
            "INSERT INTO sources (name, url_norm, owner_id, is_flash) VALUES (?, ?, ?, ?)",
            (name, norm, owner_id, 1 if is_flash else 0),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        put_conn(conn)


def update_source(source_id: int, name: str | None = None, url: str | None = None,
                  is_active: int | None = None, is_flash: int | None = None):
    """更新数据源字段"""
    conn = get_conn()
    try:
        fields, vals = [], []
        if name is not None:
            fields.append("name = ?"); vals.append(name)
        if url is not None:
            fields.append("url_norm = ?"); vals.append(normalize_url_for_db(url))
        if is_active is not None:
            fields.append("is_active = ?"); vals.append(is_active)
        if is_flash is not None:
            fields.append("is_flash = ?"); vals.append(is_flash)
        if not fields:
            return
        vals.append(source_id)
        conn.execute(f"UPDATE sources SET {', '.join(fields)} WHERE id = ?", vals)
        conn.commit()
    finally:
        put_conn(conn)


def delete_source(source_id: int):
    """删除数据源。

    sources 表：同一数据源可被多用户添加（name/url 相同，owner_id 不同）
    source_crawl_configs 表：按 source_id 全局唯一

    删除逻辑：只删 sources 记录，source_crawl_configs 由级联外键删除。
    """
    conn = get_conn()
    try:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()
    finally:
        put_conn(conn)


# ============ source_crawl_configs CRUD（按 url_norm 索引）============


def get_crawl_config(url: str) -> dict | None:
    """通过 URL（自动规范化）获取抓取配置"""
    conn = get_conn()
    try:
        norm = normalize_url_for_db(url)
        if not norm:
            return None
        rows = _dict(conn,
            "SELECT * FROM source_crawl_configs WHERE url_norm = ?",
            (norm,),
        )
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def get_crawl_config_by_url(url: str) -> dict | None:
    """通过 URL（自动规范化）获取抓取配置"""
    conn = get_conn()
    try:
        norm = normalize_url_for_db(url)
        if not norm:
            return None
        rows = _dict(conn,
            "SELECT * FROM source_crawl_configs WHERE url_norm = ?",
            (norm,),
        )
        return rows[0] if rows else None
    finally:
        put_conn(conn)




def find_learned_config_by_name(source_name: str) -> dict | None:
    """通过数据源名称查找任意已学习（有 list_config）的配置"""
    conn = get_conn()
    try:
        rows = _dict(conn,
            "SELECT * FROM source_crawl_configs WHERE name = ? AND list_config IS NOT NULL AND list_config != ''",
            (source_name,),
        )
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def get_crawl_config_by_name(source_name: str) -> dict | None:
    """通过数据源名称查找配置（用于去重）"""
    if not source_name:
        return None
    conn = get_conn()
    try:
        rows = _dict(conn,
            "SELECT * FROM source_crawl_configs WHERE name = ?",
            (source_name,),
        )
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def get_crawl_config_by_domain(domain: str) -> dict | None:
    """通过域名查找配置（用于域名级别去重）"""
    if not domain:
        return None
    conn = get_conn()
    try:
        rows = _dict(conn,
            "SELECT * FROM source_crawl_configs WHERE url_norm LIKE ?",
            (f"%://{domain}/%",),
        )
        return rows[0] if rows else None
    finally:
        put_conn(conn)


def extract_domain(url: str) -> str:
    """从 URL 提取域名，如 https://www.cnstock.com/article -> www.cnstock.com"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc


def ensure_crawl_config(source_id: int, name: str | None = None,
                          url: str | None = None) -> bool:
    """
    确保 source_crawl_configs 表中该 URL 的记录存在。
    如果不存在，插入一条空配置（按规范化 URL）。
    """
    conn = get_conn()
    try:
        norm = normalize_url_for_db(url) if url else ""
        if not norm:
            return False

        # 按规范化 URL 查重
        existing = conn.execute(
            "SELECT id FROM source_crawl_configs WHERE url_norm = ?",
            (norm,),
        ).fetchone()
        if existing:
            return False

        conn.execute(
            "INSERT INTO source_crawl_configs (url_norm, name) VALUES (?, ?)",
            (norm, name),
        )
        conn.commit()
        return True
    finally:
        put_conn(conn)


def upsert_crawl_config(url: str | None = None,
                        name: str | None = None,
                        source_type: str | None = None,
                        is_flash: int | None = None,
                        content_extract: str | None = None,
                        publish_time_pattern: str | None = None,
                        list_config: dict | None = None,
                        checked: int | None = None,
                        crawl_order: int | None = None) -> int:
    """
    按规范化 URL 插入或更新抓取配置。
    """
    conn = get_conn()
    try:
        norm = normalize_url_for_db(url) if url else ""

        # 查是否已存在
        existing = None
        if norm:
            existing = conn.execute(
                "SELECT id FROM source_crawl_configs WHERE url_norm = ?",
                (norm,),
            ).fetchone()

        if not existing:
            fields, vals = ["url_norm", "name"], [norm, name]
            if checked is not None:
                fields.append("checked"); vals.append(checked)
            placeholders = ", ".join(["?"] * len(fields))
            conn.execute(
                f"INSERT INTO source_crawl_configs ({', '.join(fields)}) VALUES ({placeholders})",
                vals,
            )

        # 动态构建更新字段列表
        set_clauses, params = [], []
        # name 只在 INSERT 时写入，UPDATE 时不覆盖（避免重新学习时覆盖原有名称）
        if source_type is not None:
            set_clauses.append("source_type = ?"); params.append(source_type)
        if is_flash is not None:
            set_clauses.append("is_flash = ?"); params.append(is_flash)
        if content_extract is not None:
            set_clauses.append("content_extract = ?"); params.append(content_extract)
        if publish_time_pattern is not None:
            set_clauses.append("publish_time_pattern = ?"); params.append(publish_time_pattern)
        if list_config is not None:
            set_clauses.append("list_config = ?"); params.append(json.dumps(list_config, ensure_ascii=False))
        if crawl_order is not None:
            set_clauses.append("crawl_order = ?"); params.append(crawl_order)
        if checked is not None:
            set_clauses.append("checked = ?"); params.append(checked)

        if set_clauses:
            set_clauses.append("updated_at = datetime('now','localtime')")
            params.append(norm)
            conn.execute(
                f"UPDATE source_crawl_configs SET {', '.join(set_clauses)} WHERE url_norm = ?",
                params,
            )
        conn.commit()
        return existing[0] if existing else 0
    finally:
        put_conn(conn)


def delete_crawl_config(source_id: int):
    """通过 source_id 查找 url_norm，检查是否还有其他数据源使用该 url_norm，只有在没有其他数据源时才删除 source_crawl_configs 对应记录"""
    conn = get_conn()
    try:
        source_rows = _dict(conn, "SELECT url_norm FROM sources WHERE id = ?", (source_id,))
        if source_rows:
            norm = source_rows[0].get("url_norm", "")
            if norm:
                # 检查是否还有其他活跃数据源使用该 url_norm（排除当前要删除的 source_id）
                other_count = conn.execute(
                    "SELECT COUNT(*) FROM sources WHERE url_norm = ? AND id != ?",
                    (norm, source_id),
                ).fetchone()[0]
                if other_count == 0:
                    conn.execute("DELETE FROM source_crawl_configs WHERE url_norm = ?", (norm,))
                    conn.commit()
    finally:
        put_conn(conn)


def get_content_extract_by_name(source_name: str) -> str | None:
    """通过数据源名称获取 content_extract；不存在或为空返回 None。"""
    conn = get_conn()
    try:
        config_rows = _dict(conn,
            "SELECT content_extract FROM source_crawl_configs WHERE name = ?",
            (source_name,),
        )
        return config_rows[0].get("content_extract") if config_rows else None
    finally:
        put_conn(conn)


def get_publish_time_extract_by_name(source_name: str) -> str | None:
    """通过数据源名称获取 publish_time_pattern；不存在或为空返回 None。"""
    conn = get_conn()
    try:
        config_rows = _dict(conn,
            "SELECT publish_time_pattern FROM source_crawl_configs WHERE name = ?",
            (source_name,),
        )
        return config_rows[0].get("publish_time_pattern") if config_rows else None
    finally:
        put_conn(conn)


def get_content_extract_config(source_name: str) -> dict | None:
    """通过数据源名称获取 content_extract 配置（JSON 解析后返回 dict）"""
    conn = get_conn()
    try:
        config_rows = _dict(conn,
            "SELECT content_extract FROM source_crawl_configs WHERE name = ?",
            (source_name,),
        )
        if not config_rows:
            return None
        content_extract = config_rows[0].get("content_extract", "")
        if not content_extract:
            return None
        return parse_json_field(content_extract)
    finally:
        put_conn(conn)


# ============ 联合查询 ============


def list_sources_with_configs(owner_id: int | None = None, include_inactive: bool = False):
    """
    从 source_crawl_configs 表查询，按 url_norm 去重。
    注意：此方法对应 source_crawl_configs 表，用于爬虫采集，不要与 sources 表混淆。
    """
    conn = get_conn()
    try:
        config_rows = _dict(conn, "SELECT * FROM source_crawl_configs ORDER BY id", ())
        if not config_rows:
            return []

        result = []
        for c in config_rows:
            norm = c.get("url_norm", "")
            if not norm:
                continue

            entry = {
                "name": c.get("name") or "",
                "url_norm": norm,
                "url": norm,
                "config_id": c.get("id"),
                "config_name": c.get("name"),
                "source_type": c.get("source_type"),
                "content_extract": c.get("content_extract"),
                "publish_time_pattern": c.get("publish_time_pattern"),
                "list_config": c.get("list_config"),
                "crawl_order": c.get("crawl_order") or 100,
                "checked": c.get("checked", 0),
                "is_flash": c.get("is_flash", 0),
            }
            result.append(entry)
        return result
    finally:
        put_conn(conn)


def get_all_source_names() -> set[str]:
    """获取 source_crawl_configs 中所有数据源名称"""
    conn = get_conn()
    try:
        rows = _dict(conn, "SELECT name FROM source_crawl_configs WHERE name IS NOT NULL AND name != ''", ())
        return {r["name"] for r in rows}
    finally:
        put_conn(conn)


def list_user_sources(owner_id: int | None = None, include_inactive: bool = False):
    """
    从 sources 表查询用户数据源，按 url_norm 去重后附加 config 信息。
    用于 API 返回用户相关的数据源列表。
    """
    conn = get_conn()
    try:
        conditions = ["1=1"]
        params = []
        if owner_id is not None:
            conditions.append("owner_id = ?")
            params.append(owner_id)
        if not include_inactive:
            conditions.append("is_active = 1")
        where = " AND ".join(conditions)
        sources_rows = _dict(conn,
            f"""SELECT id, name, url_norm, owner_id, is_active, is_flash, created_at
               FROM sources WHERE {where} ORDER BY id""",
            params,
        )
        # 按 url_norm 去重，取每条 url_norm 的第一条
        seen_norm = set()
        unique_sources = []
        for s in sources_rows:
            norm = s.get("url_norm") or ""
            if norm and norm not in seen_norm:
                seen_norm.add(norm)
                unique_sources.append(s)

        # 加载所有 configs，按 url_norm 构建索引
        config_rows = _dict(conn, "SELECT * FROM source_crawl_configs", ())
        config_by_norm = {c["url_norm"]: c for c in config_rows}

        result = []
        for s in unique_sources:
            norm = s.get("url_norm") or ""
            c = config_by_norm.get(norm, {})
            entry = dict(s)
            entry["url"] = norm
            entry["config_id"] = c.get("id")
            entry["config_name"] = c.get("name")
            entry["source_type"] = c.get("source_type")
            entry["content_extract"] = c.get("content_extract")
            entry["publish_time_pattern"] = c.get("publish_time_pattern")
            entry["list_config"] = c.get("list_config")
            result.append(entry)
        return result
    finally:
        put_conn(conn)


# ============ 工具 ============
from script.db.connection import rows_to_dicts as _dict