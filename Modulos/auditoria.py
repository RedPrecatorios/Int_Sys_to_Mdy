from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_logger = logging.getLogger(__name__)

# Valores para coluna monday_resultado (request_audit).
MONDAY_RESULTADO_IGNORADO = "ignorado"
MONDAY_RESULTADO_SUCESSO = "tentado_sucesso"
MONDAY_RESULTADO_ERRO = "tentado_erro"
MONDAY_RESULTADO_NAO_TENTADO = "nao_tentado"

_RESULTADOS_VALIDOS = frozenset(
    {
        MONDAY_RESULTADO_IGNORADO,
        MONDAY_RESULTADO_SUCESSO,
        MONDAY_RESULTADO_ERRO,
        MONDAY_RESULTADO_NAO_TENTADO,
    }
)


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
    # Sessão MySQL ao gravar NOW(): ex. -03:00 ou America/Sao_Paulo. None = não altera (relógio do servidor).
    mysql_session_timezone: Optional[str]


def _env_first(*names: str, default: str = "") -> str:
    """Primeiro getenv não vazio entre várias chaves (ex.: MYSQL_* ou EDA_*)."""
    for name in names:
        raw = os.getenv(name)
        if raw is not None and str(raw).strip() != "":
            return str(raw).strip()
    return default


_MYSQL_TZ_SAFE = re.compile(r"^(?:UTC|[+-][0-9]{2}:[0-9]{2}|[A-Za-z0-9_/+-]+)$")


def _mysql_session_timezone_from_env() -> Optional[str]:
    """
    Fuso da sessão MySQL para NOW() na auditoria.
    - Variável ausente: default -03:00 (Brasil, sem DST).
    - Variável definida e vazia: não altera o time_zone da sessão (comportamento antigo).
    """
    for key in ("MYSQL_SESSION_TIME_ZONE", "EDA_MYSQL_SESSION_TIME_ZONE"):
        if os.environ.get(key) is not None:
            raw = str(os.environ.get(key, "")).strip()
            return raw if raw else None
    return "-03:00"


def _validate_mysql_session_timezone(tz: str) -> Optional[str]:
    s = str(tz).strip()
    if not s or ".." in s or len(s) > 64:
        return None
    if not _MYSQL_TZ_SAFE.match(s):
        return None
    return s


def load_audit_config() -> AuditConfig:
    mode = os.getenv("AUDIT_MODE", "file").strip().lower()
    if mode not in {"off", "file", "mysql", "both"}:
        mode = "file"

    raw_tz = _mysql_session_timezone_from_env()
    mysql_tz = _validate_mysql_session_timezone(raw_tz) if raw_tz else None
    if raw_tz and not mysql_tz:
        _logger.warning(
            "MYSQL_SESSION_TIME_ZONE inválido (%r); não alterando time_zone da sessão MySQL.",
            raw_tz,
        )

    return AuditConfig(
        mode=mode,
        log_path=os.getenv("AUDIT_LOG_PATH", "logs/requisicoes_incluir.jsonl"),
        mysql_host=_env_first("MYSQL_HOST", "EDA_MYSQL_HOST", default="127.0.0.1"),
        mysql_port=int(_env_first("MYSQL_PORT", "EDA_MYSQL_PORT", default="3306")),
        mysql_db=_env_first("MYSQL_DB", "EDA_MYSQL_DATABASE", default="int_sys_to_mdy"),
        mysql_user=_env_first("MYSQL_USER", "EDA_MYSQL_USER", default="int_sys_to_mdy"),
        mysql_password=_env_first("MYSQL_PASSWORD", "EDA_MYSQL_PASSWORD", default=""),
        mysql_table=os.getenv("MYSQL_AUDIT_TABLE", "request_audit").strip() or "request_audit",
        mysql_session_timezone=mysql_tz,
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


def _lower_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(k).lower().strip().replace(" ", "_").replace(".", "_"): v
        for k, v in d.items()
    }


def _get_ci(d: Dict[str, Any], *names: str) -> Any:
    """Primeiro valor encontrado por nomes de chave (insensível a maiúsculas / espaços)."""
    ld = _lower_dict(d)
    for n in names:
        key = n.lower().strip().replace(" ", "_").replace(".", "_")
        if key in ld:
            return ld[key]
    return None


def _inner_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(p, dict):
        return {}
    inner = p.get("payload")
    if isinstance(inner, dict) and ("received_at" in p or "client_ip" in p):
        return inner
    return p


def _dedup_key(inner: Dict[str, Any], request_uuid: str) -> str:
    lid = _get_ci(inner, "ligacao_id", "ligacao id")
    if lid is not None and str(lid).strip() != "":
        try:
            return f"ligacao:{int(lid)}"
        except (ValueError, TypeError):
            return f"ligacao:{lid}"[:160]

    ext = _get_ci(inner, "id")
    if ext is not None and str(ext).strip() != "" and _get_ci(inner, "agente") is not None:
        return f"externo:{ext}"[:160]

    nc = _get_ci(inner, "numero_do_cumprimento", "numero do cumprimento")
    if nc is not None and str(nc).strip() != "":
        return f"cumprimento:{nc}"[:160]

    proc = _get_ci(inner, "processo", "processo_principal")
    if proc is not None and str(proc).strip() != "" and _get_ci(inner, "numero_do_incidente", "incidente") is not None:
        return f"prc:{proc}"[:160]

    return f"request:{request_uuid}"


def _extract_mailing(inner: Dict[str, Any]) -> Optional[str]:
    for key in ("mailing", "mailing_nome", "nome_mailing", "campanha", "mailing_name", "nome_mailing_lista"):
        v = _get_ci(inner, key)
        if v is not None and str(v).strip():
            return str(v).strip()[:512]

    raw = _get_ci(inner, "custom_data")
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        arr = json.loads(s)
        if isinstance(arr, list):
            for item in arr:
                t = str(item).strip()
                low = t.lower()
                for prefix in ("mailing:", "campanha:", "mailing "):
                    if low.startswith(prefix):
                        return t.split(":", 1)[-1].strip()[:512]
    except json.JSONDecodeError:
        pass

    normalized = s.replace("\\r\\n", "\n").replace("\r\n", "\n")
    for line in normalized.split("\n"):
        if "mail" in line.lower() and ":" in line:
            return line.split(":", 1)[-1].strip()[:512]
    return None


def _only_digits(s: str, max_len: int = 32) -> Optional[str]:
    d = "".join(c for c in s if c.isdigit())
    return d[:max_len] if d else None


def _parse_credor_campos(inner: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Nome / CPF / telefone do credor (custom_data em lista JSON de linhas 'Chave: valor')
    ou campos directos no payload (credor_nome, cpf_credor, …).
    """
    nome: Optional[str] = None
    cpf: Optional[str] = None
    tel: Optional[str] = None

    for key in ("credor_nome", "nome_credor", "nome_devedor"):
        v = _get_ci(inner, key)
        if v is not None and str(v).strip():
            nome = str(v).strip()[:512]
            break
    for key in ("credor_cpf", "cpf_credor"):
        v = _get_ci(inner, key)
        if v is not None and str(v).strip():
            cpf = _only_digits(str(v), 20)
            break
    for key in ("credor_telefone", "telefone_credor"):
        v = _get_ci(inner, key)
        if v is not None and str(v).strip():
            tel = _only_digits(str(v), 32)
            break

    raw = _get_ci(inner, "custom_data")
    if raw is not None and str(raw).strip():
        s = str(raw).strip()
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                for item in arr:
                    line = str(item).strip()
                    if ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    key = k.strip().lower()
                    val = v.strip()
                    if not val:
                        continue
                    if key == "nome" or key.startswith("nome ") or key == "requerente" or key.startswith("requerente "):
                        nome = val[:512]
                    elif key == "cpf" or key.startswith("cpf"):
                        d = _only_digits(val, 20)
                        if d:
                            cpf = d
                    elif "telefone" in key or key == "tel" or key.startswith("telefone"):
                        d = _only_digits(val, 32)
                        if d:
                            tel = d
        except json.JSONDecodeError:
            pass

    return (
        nome.strip()[:512] if nome else None,
        cpf if cpf else None,
        tel if tel else None,
    )


def _insert_mysql(cfg: AuditConfig, record: Dict[str, Any]) -> None:
    try:
        import mysql.connector  # type: ignore
    except Exception as e:
        raise RuntimeError("Dependência mysql-connector-python não instalada.") from e

    inner = _inner_payload(record.get("payload") or {})
    rid = str(record.get("id") or "")
    dedup = _dedup_key(inner, rid or str(uuid.uuid4()))

    user_usuario = _get_ci(inner, "user_usuario")
    user_nome = _get_ci(inner, "user_nome")
    ligacao_id_raw = _get_ci(inner, "ligacao_id", "ligacao id")
    ligacao_id: Optional[int] = None
    if ligacao_id_raw is not None and str(ligacao_id_raw).strip() != "":
        try:
            ligacao_id = int(ligacao_id_raw)
        except (ValueError, TypeError):
            ligacao_id = None

    acionamento = _get_ci(inner, "ligacao_acionamento", "ligacao acionamento")
    mailing = _extract_mailing(inner)
    credor_nome, credor_cpf, credor_tel = _parse_credor_campos(inner)

    su = str(user_usuario).strip()[:190] if user_usuario is not None else None
    sn = str(user_nome).strip()[:255] if user_nome is not None else None
    sa = str(acionamento).strip()[:255] if acionamento is not None else None

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
    tbl = "".join(c for c in cfg.mysql_table if c.isalnum() or c == "_") or "request_audit"
    try:
        cur = conn.cursor()
        if cfg.mysql_session_timezone:
            cur.execute("SET SESSION time_zone = %s", (cfg.mysql_session_timezone,))
        cur.execute(
            f"""
            INSERT INTO `{tbl}` (
              dedup_key, request_id, user_usuario, user_nome, credor_nome, credor_cpf, credor_telefone,
              ligacao_id, ligacao_acionamento, mailing_nome,
              primeira_requisicao_at, ultima_ligacao_at, total_ligacoes, client_ip, payload_json, headers_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(6), NOW(6), 1, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              request_id = VALUES(request_id),
              user_usuario = COALESCE(VALUES(user_usuario), user_usuario),
              user_nome = COALESCE(VALUES(user_nome), user_nome),
              credor_nome = COALESCE(VALUES(credor_nome), credor_nome),
              credor_cpf = COALESCE(VALUES(credor_cpf), credor_cpf),
              credor_telefone = COALESCE(VALUES(credor_telefone), credor_telefone),
              ligacao_id = COALESCE(VALUES(ligacao_id), ligacao_id),
              ligacao_acionamento = VALUES(ligacao_acionamento),
              mailing_nome = COALESCE(VALUES(mailing_nome), mailing_nome),
              ultima_ligacao_at = NOW(6),
              total_ligacoes = total_ligacoes + 1,
              client_ip = VALUES(client_ip),
              payload_json = VALUES(payload_json),
              headers_json = VALUES(headers_json),
              monday_resultado = NULL,
              monday_item_id = NULL,
              monday_erro = NULL,
              monday_processado_em = NULL
            """,
            (
                dedup,
                rid,
                su,
                sn,
                credor_nome,
                credor_cpf,
                credor_tel,
                ligacao_id,
                sa,
                mailing,
                record.get("client_ip"),
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


def _mysql_connect(cfg: AuditConfig):
    try:
        import mysql.connector  # type: ignore
    except Exception as e:
        raise RuntimeError("Dependência mysql-connector-python não instalada.") from e
    return mysql.connector.connect(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        database=cfg.mysql_db,
        connection_timeout=5,
    )


def _sanitize_table_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c == "_") or "request_audit"


def atualizar_resultado_monday(
    request_id: str,
    resultado: str,
    *,
    monday_item_id: Optional[int] = None,
    monday_erro: Optional[str] = None,
    cfg: Optional[AuditConfig] = None,
) -> None:
    """
    Atualiza monday_resultado / monday_item_id / monday_erro / monday_processado_em
    na linha auditada (por request_id).
    """
    if not request_id or not str(request_id).strip():
        return

    res = str(resultado).strip()
    if res not in _RESULTADOS_VALIDOS:
        _logger.warning("monday_resultado inválido (%r); update ignorado.", resultado)
        return

    cfg = cfg or load_audit_config()
    if cfg.mode not in {"mysql", "both"}:
        return

    item_id: Optional[int] = None
    if monday_item_id is not None:
        try:
            item_id = int(monday_item_id)
        except (TypeError, ValueError):
            item_id = None

    erro_txt: Optional[str] = None
    if monday_erro is not None and str(monday_erro).strip():
        erro_txt = str(monday_erro).strip()[:65535]

    tbl = _sanitize_table_name(cfg.mysql_table)
    conn = _mysql_connect(cfg)
    try:
        cur = conn.cursor()
        if cfg.mysql_session_timezone:
            cur.execute("SET SESSION time_zone = %s", (cfg.mysql_session_timezone,))
        cur.execute(
            f"""
            UPDATE `{tbl}`
            SET monday_resultado = %s,
                monday_item_id = %s,
                monday_erro = %s,
                monday_processado_em = NOW(6)
            WHERE request_id = %s
            """,
            (res, item_id, erro_txt, str(request_id).strip()),
        )
        conn.commit()
        if cur.rowcount == 0:
            _logger.warning(
                "atualizar_resultado_monday: nenhuma linha para request_id=%s (resultado=%s)",
                request_id,
                res,
            )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def registrar_resultado_monday_seguro(
    request_id: str,
    resultado: str,
    *,
    monday_item_id: Optional[int] = None,
    monday_erro: Optional[str] = None,
) -> None:
    try:
        atualizar_resultado_monday(
            request_id,
            resultado,
            monday_item_id=monday_item_id,
            monday_erro=monday_erro,
        )
    except Exception as e:
        _logger.warning("Falha ao gravar resultado Monday no MySQL: %s", e)

