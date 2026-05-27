-- Int_Sys_to_Mdy — base e tabela de auditoria (UPSERT + pesquisa por operador e credor)
-- Execute como utilizador com permissão CREATE (ex.: root).
-- Para `plataforma_central`: USE plataforma_central;

CREATE DATABASE IF NOT EXISTS int_sys_to_mdy
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE int_sys_to_mdy;

-- Se migrar da tabela antiga: RENAME TABLE request_audit TO request_audit_legacy;
-- Se já existir request_audit sem as colunas credor_*: execute sql/migrate_request_audit_search.sql

CREATE TABLE IF NOT EXISTS request_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  dedup_key VARCHAR(160) NOT NULL COMMENT 'ligacao:ID | externo:ID | cumprimento:NUM | request:UUID',
  request_id CHAR(36) NOT NULL,
  user_usuario VARCHAR(190) NULL COMMENT 'Operador (login)',
  user_nome VARCHAR(255) NULL COMMENT 'Operador (nome) — pesquisa LIKE',
  credor_nome VARCHAR(512) NULL COMMENT 'Nome do credor/devedor extraído de custom_data (ex.: Nome: ...)',
  credor_cpf VARCHAR(20) NULL COMMENT 'Só dígitos — pesquisa exacta/prefixo',
  credor_telefone VARCHAR(32) NULL COMMENT 'Só dígitos — pesquisa',
  ligacao_id BIGINT NULL,
  ligacao_acionamento VARCHAR(255) NULL,
  mailing_nome VARCHAR(512) NULL,
  -- NOW() na app usa time_zone da sessão (ver MYSQL_SESSION_TIME_ZONE no .env); default MySQL = relógio do servidor.
  primeira_requisicao_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  ultima_ligacao_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  total_ligacoes INT UNSIGNED NOT NULL DEFAULT 1,
  client_ip VARCHAR(128) NULL,
  payload_json JSON NOT NULL,
  headers_json JSON NULL,
  monday_resultado VARCHAR(20) NULL
    COMMENT 'ignorado | tentado_sucesso | tentado_erro | nao_tentado',
  monday_item_id BIGINT UNSIGNED NULL COMMENT 'ID do item na Monday (sucesso)',
  monday_erro TEXT NULL COMMENT 'Mensagem de erro da Monday ou validação',
  monday_processado_em DATETIME(6) NULL COMMENT 'Quando o resultado Monday foi gravado',
  PRIMARY KEY (id),
  UNIQUE KEY uq_request_audit_dedup (dedup_key),
  KEY idx_request_audit_ligacao (ligacao_id),
  KEY idx_request_audit_ultima (ultima_ligacao_at),
  KEY idx_request_audit_user_usuario (user_usuario(64)),
  KEY idx_request_audit_user_nome (user_nome(128)),
  KEY idx_request_audit_credor_nome (credor_nome(128)),
  KEY idx_request_audit_credor_cpf (credor_cpf),
  KEY idx_request_audit_credor_tel (credor_telefone),
  KEY idx_request_audit_monday (monday_resultado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- GRANT SELECT, INSERT, UPDATE ON plataforma_central.request_audit TO 'eda_app'@'%';
-- FLUSH PRIVILEGES;

-- Exemplos de pesquisa:
-- SELECT * FROM request_audit WHERE user_nome LIKE '%Thayana%';
-- SELECT * FROM request_audit WHERE credor_nome LIKE '%CARLOS ALBERTO%';
-- SELECT * FROM request_audit WHERE credor_cpf LIKE '8696972856%';
-- SELECT * FROM request_audit WHERE credor_telefone LIKE '%12996501236%';
