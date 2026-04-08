from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditConfig:
    mode: str  # off|file|mysql|both
    log_path: str

    mysql_host: str
    mysql_port: int
    mysql_db: str
    mysql_user: str
    mysql_password: str
    mysql_table: str


def load_audit_config() -> AuditConfig:
    mode = os.getenv("AUDIT_MODE", "file").strip().lower()
    if mode not in {"off", "file", "mysql", "both"}:
        mode = "file"

    return AuditConfig(
        mode=mode,
        log_path=os.getenv("AUDIT_LOG_PATH", "logs/requisicoes_incluir.jsonl"),
        mysql_host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
        mysql_db=os.getenv("MYSQL_DB", "int_sys_to_mdy"),
        mysql_user=os.getenv("MYSQL_USER", "int_sys_to_mdy"),
        mysql_password=os.getenv("MYSQL_PASSWORD", ""),
        mysql_table=os.getenv("MYSQL_AUDIT_TABLE", "request_audit"),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _append_jsonl(path: str, record: Dict[str, Any]) -> None:
    _ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _insert_mysql(cfg: AuditConfig, record: Dict[str, Any]) -> None:
    try:
        import mysql.connector  # type: ignore
    except Exception as e:
        raise RuntimeError("Dependência mysql-connector-python não instalada.") from e

    payload_json = json.dumps(record.get("payload"), ensure_ascii=False)
    headers_json = json.dumps(record.get("headers"), ensure_ascii=False)

    conn = mysql.connector.connect(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        database=cfg.mysql_db,
        connection_timeout=5,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO `{cfg.mysql_table}`
            (`id`, `received_at`, `client_ip`, `path`, `payload_json`, `headers_json`)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                record["id"],
                record["received_at"],
                record.get("client_ip"),
                record.get("path"),
                payload_json,
                headers_json,
            ),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def registrar_requisicao_incluir(
    *,
    client_ip: str,
    path: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    cfg: Optional[AuditConfig] = None,
) -> str:
    """
    Registra o payload recebido no POST /incluir.
    Retorna um request_id (UUID) para rastreio em logs.
    """
    cfg = cfg or load_audit_config()
    rid = str(uuid.uuid4())

    record: Dict[str, Any] = {
        "id": rid,
        "received_at": _utc_now_iso(),
        "client_ip": client_ip,
        "path": path,
        "payload": payload,
        "headers": headers or {},
    }

    if cfg.mode in {"file", "both"}:
        _append_jsonl(cfg.log_path, record)

    if cfg.mode in {"mysql", "both"}:
        _insert_mysql(cfg, record)

    return rid

