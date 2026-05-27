-- Migração: colunas credor_* + índices para pesquisa (operador e credor)
-- Ajuste: USE plataforma_central;
--
-- Se alguma coluna/índice já existir, remova essa linha e volte a executar.

ALTER TABLE request_audit
  ADD COLUMN credor_nome VARCHAR(512) NULL COMMENT 'Nome credor (custom_data)' AFTER user_nome,
  ADD COLUMN credor_cpf VARCHAR(20) NULL AFTER credor_nome,
  ADD COLUMN credor_telefone VARCHAR(32) NULL AFTER credor_cpf;

CREATE INDEX idx_request_audit_user_nome ON request_audit (user_nome(128));
CREATE INDEX idx_request_audit_credor_nome ON request_audit (credor_nome(128));
CREATE INDEX idx_request_audit_credor_cpf ON request_audit (credor_cpf);
CREATE INDEX idx_request_audit_credor_tel ON request_audit (credor_telefone);
