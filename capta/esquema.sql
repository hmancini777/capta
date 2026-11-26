-- ============================================================================
-- Banco de dados do Capta (SQLite).
--
-- Este arquivo roda toda vez que o sistema abre o banco. Ele só cria o que
-- ainda não existe, então pode rodar quantas vezes for preciso sem apagar nada.
--
-- São 5 tabelas:
--   cards     -> tudo que espera uma decisão humana no Telegram
--   recados   -> texto livre que o operador manda ao bot (instruções)
--   leads     -> o CRM: cada potencial cliente e em que etapa do funil ele está
--   mensagens -> cada texto escrito para um lead (1ª mensagem, follow-ups, respostas)
--   estado    -> configurações e memória do bot (modo, último lote, etc.)
-- ============================================================================

-- CARDS: a "caixa de aprovação". Cada mensagem que um agente escreve vira um
-- card no Telegram com botões. Nada sai para um lead sem passar por aqui.
CREATE TABLE IF NOT EXISTS cards (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo        TEXT NOT NULL,                     -- revisao, dm, followup, resposta, teste
  ref         TEXT,                              -- a que o card se refere. Ex.: "msg:12" = mensagem 12
  texto       TEXT NOT NULL,                     -- o que aparece no card (HTML do Telegram)
  msg_id      INTEGER,                           -- id da mensagem no Telegram (para ler respostas ao card)
  status      TEXT NOT NULL DEFAULT 'pendente',  -- pendente, aprovado, ajustar, descartado, enviado, pulado
  nota        TEXT,                              -- correção que o operador escreveu respondendo ao card
  criado_em   TEXT NOT NULL,
  decidido_em TEXT
);

-- RECADOS: mensagens livres do operador para o sistema ("hoje foca em Moema").
-- O agente lê na próxima rodada e marca como lido.
CREATE TABLE IF NOT EXISTS recados (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  texto     TEXT NOT NULL,
  lido      INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL
);

-- LEADS: o CRM. Um lead é um potencial cliente (aqui: clínica ou profissional).
-- A coluna "estagio" diz em que ponto do funil ele está (ver docs/04-dados.md).
CREATE TABLE IF NOT EXISTS leads (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  nome          TEXT NOT NULL,                   -- como aparece para o público: "Dra. Camila Rocha"
  instagram     TEXT UNIQUE,                     -- usuário sem @, minúsculo. UNIQUE = nunca contatar 2 vezes
  whatsapp      TEXT,                            -- só dígitos, com 55 na frente
  email         TEXT,
  bairro        TEXT,
  fonte         TEXT,                            -- onde foi achado: maps, instagram, indicacao, inbound
  sinais        TEXT,                            -- por que é um bom lead, com dado concreto
  seguidores    INTEGER,
  pontos        INTEGER,                         -- nota de 0 a 10 (skill capta-prospeccao, referencias/criterios-lead.md)
  estagio       TEXT NOT NULL DEFAULT 'novo',    -- novo, qualificado, rascunho, enviado, respondeu,
                                                 -- diagnostico, reuniao, cliente, perdido, descartado
  proximo_passo TEXT,                            -- fu1, fu2, responder, reedicao, reuniao
  proximo_em    TEXT,                            -- quando fazer o próximo passo (AAAA-MM-DD)
  evento        TEXT,                            -- id do evento na agenda, quando há reunião marcada
  notas         TEXT,
  criado_em     TEXT NOT NULL,
  atualizado_em TEXT NOT NULL
);

-- MENSAGENS: cada texto rascunhado para um lead. O card aponta para cá com
-- ref "msg:<id>", e o bot leva a decisão do botão até a mensagem e o lead.
CREATE TABLE IF NOT EXISTS mensagens (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id    INTEGER NOT NULL REFERENCES leads(id),
  tipo       TEXT NOT NULL,                    -- dm1 (1ª mensagem), fu1, fu2 (follow-ups),
                                               -- recebida (o que o lead disse), resposta, diagnostico
  canal      TEXT NOT NULL,                    -- instagram, whatsapp, email
  texto      TEXT NOT NULL,
  contexto   TEXT,                             -- o que o card mostra acima do texto (ex.: Reel citado)
  status     TEXT NOT NULL DEFAULT 'rascunho', -- rascunho, aprovada, no_card, enviado,
                                               -- ajustar, refeita, descartado, recebida
  card_id    INTEGER,
  criado_em  TEXT NOT NULL,
  enviado_em TEXT
);

-- ESTADO: pares chave/valor que o bot precisa lembrar entre uma execução e outra.
--   modo_dm  -> "revisao" (só aprova textos) ou "envio" (textos vêm com botão Enviei)
--   lote_dia -> data do último lote automático (para não mandar 2 vezes no mesmo dia)
--   offset   -> até onde o bot já leu as mensagens do Telegram
CREATE TABLE IF NOT EXISTS estado (
  chave TEXT PRIMARY KEY,
  valor TEXT
);
