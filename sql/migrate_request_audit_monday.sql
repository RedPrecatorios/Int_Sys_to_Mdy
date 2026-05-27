-- Colunas de controlo da integração Monday (se ainda não existirem).
-- Execute em plataforma_central (ou a base do MYSQL_AUDIT_TABLE).

ALTER TABLE request_audit
  ADD COLUMN IF NOT EXISTS monday_resultado VARCHAR(20) NULL
    COMMENT 'ignorado | tentado_sucesso | tentado_erro | nao_tentado',
  ADD COLUMN IF NOT EXISTS monday_item_id BIGINT UNSIGNED NULL,
  ADD COLUMN IF NOT EXISTS monday_erro TEXT NULL,
  ADD COLUMN IF NOT EXISTS monday_processado_em DATETIME(6) NULL;

-- MySQL < 8.0.12 não tem IF NOT EXISTS em ADD COLUMN — use só as linhas que faltarem.

CREATE INDEX IF NOT EXISTS idx_request_audit_monday ON request_audit (monday_resultado);
