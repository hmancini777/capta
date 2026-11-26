"""Bot do Capta no Telegram: a ponte entre os agentes de IA e o humano que aprova.

O QUE ELE FAZ
  - Manda "cards" para o Telegram do operador: cada card é uma mensagem escrita
    por um agente de IA, com botões (Aprovar, Ajustar, Descartar, Enviei, Pular).
  - Grava no banco o botão que o operador apertou e leva essa decisão até a
    mensagem e o lead (ex.: "Enviei" agenda o follow-up para daqui a 3 dias).
  - Em dia útil, a partir das 12h, manda sozinho o lote de mensagens do dia.

O QUE ELE NÃO FAZ
  - Não chama IA. Quem pesquisa e escreve são os agentes de IA (.claude/agents/ e automacao/).
    O bot é só automação: regras fixas, sem "inteligência".
  - Não envia nada para lead. Quem envia é o humano, copiando o texto do card.

MODO DEMO
  Sem token do Telegram (ou com CAPTA_DEMO=1), o bot não acessa a internet:
  os cards aparecem no terminal. É assim que o demo/demo.py roda em qualquer PC.

USO
  python capta/bot.py parear      grava o chat de quem mandou /start ao bot
  python capta/bot.py rodar       liga o bot (fica ouvindo os botões)
  python capta/bot.py teste       manda um card de teste
  python capta/bot.py card <json> manda um card descrito num arquivo JSON

Comandos no chat do Telegram:
  /status                          resumo de cards e leads
  /lote                            manda o lote de mensagens agora
  /modo revisao | /modo envio      troca o tipo de card (ver docs/03-automacao.md)
  /resp @usuario <texto>           registra que o lead respondeu
  /reuniao @usuario 07/11 09:40    marca uma reunião (sem argumentos, lista horários livres)
"""
import html
import json
import os
import pathlib
import re
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Caminhos e configuração. Tudo relativo à pasta do projeto, para rodar em
# qualquer computador. Dá para trocar por variável de ambiente.
# ---------------------------------------------------------------------------
RAIZ = pathlib.Path(__file__).resolve().parent.parent
BANCO = pathlib.Path(os.environ.get("CAPTA_BANCO", RAIZ / "dados" / "capta.sqlite"))
ESQUEMA = RAIZ / "capta" / "esquema.sql"
LOG = pathlib.Path(os.environ.get("CAPTA_LOG", RAIZ / "dados" / "bot.log"))
ENV = pathlib.Path(os.environ.get("CAPTA_ENV", RAIZ / ".env"))  # token fica aqui, fora do Git

PORTA_TRAVA = 47613   # impede dois bots rodando ao mesmo tempo (brigariam pelas mensagens)
HORA_LOTE = (12, 18)  # o lote automático sai entre 12h e 17h59, uma vez por dia útil

ROTULOS = {"aprovar": "Aprovar", "ajustar": "Ajustar", "descartar": "Descartar",
           "enviei": "Enviei", "pular": "Pular"}
# botão apertado -> status do card
STATUS = {"aprovar": "aprovado", "ajustar": "ajustar", "descartar": "descartado",
          "enviei": "enviado", "pular": "pulado"}
# status do card -> status da mensagem. "Pular" devolve a mensagem para o próximo lote.
CARD_PARA_MSG = {"aprovado": "aprovada", "enviado": "enviado", "pulado": "rascunho",
                 "ajustar": "ajustar", "descartado": "descartado"}
# Cadência de follow-up: depois de enviar a dm1, o fu1 vence em 3 dias;
# depois do fu1, o fu2 vence em mais 4 (7º dia). Depois do fu2, o sistema para de insistir.
SEGUINTE = {"dm1": ("fu1", 3), "fu1": ("fu2", 4)}
# Mensagens de conversa (o lead já respondeu): que estágio e próximo passo o lead ganha.
DEPOIS_DA_CONVERSA = {"resposta": (None, None), "diagnostico": ("diagnostico", "reedicao")}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def hoje():
    """Data de hoje. CAPTA_HOJE=AAAA-MM-DD finge outra data (a demo usa para 'pular' dias)."""
    falso = os.environ.get("CAPTA_HOJE")
    return date.fromisoformat(falso) if falso else date.today()


def agora():
    return f"{hoje().isoformat()} {datetime.now():%H:%M:%S}"


_ultimo_log = [None]


def log(msg):
    if msg == _ultimo_log[0]:
        return  # sem internet o mesmo erro se repetiria a cada 5 s
    _ultimo_log[0] = msg
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{agora()} {msg}\n")


def ler_env():
    """Lê o arquivo .env (TELEGRAM_TOKEN e TELEGRAM_CHAT_ID). Nunca vai para o GitHub."""
    env = {}
    if ENV.exists():
        for linha in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def gravar_env(chave, valor):
    env = ler_env()
    env[chave] = valor
    ENV.write_text("".join(f"{k}={v}\n" for k, v in env.items()), encoding="utf-8")


def modo_demo():
    return os.environ.get("CAPTA_DEMO") == "1" or not ler_env().get("TELEGRAM_TOKEN")


def chat_id():
    return int(ler_env().get("TELEGRAM_CHAT_ID", "0") or 0)


# ---------------------------------------------------------------------------
# Telegram (ou terminal, no modo demo)
# ---------------------------------------------------------------------------
_demo_msg_id = [1000]


def _mostrar_no_terminal(params):
    """Desenha no terminal o que iria para o Telegram."""
    texto = re.sub(r"</?(b|pre)>", "", params.get("text", ""))
    texto = html.unescape(texto)
    print("  ┌" + "─" * 66)
    for linha in texto.splitlines():
        print("  │ " + linha)
    teclado_ = (params.get("reply_markup") or {}).get("inline_keyboard", [])
    botoes = [b["text"] for linha in teclado_ for b in linha if "callback_data" in b]
    links = [b["text"] for linha in teclado_ for b in linha if "url" in b]
    if botoes:
        print("  │ " + "  ".join(f"[{b}]" for b in botoes))
    if links:
        print("  │ " + "  ".join(f"<{l}>" for l in links))
    print("  └" + "─" * 66)


def api(metodo, **params):
    """Chama a API do Telegram. No modo demo, só imprime e devolve uma resposta falsa."""
    if modo_demo():
        if metodo == "sendMessage":
            _mostrar_no_terminal(params)
        _demo_msg_id[0] += 1
        return {"message_id": _demo_msg_id[0]}
    token = ler_env()["TELEGRAM_TOKEN"]
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=json.dumps(params).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=params.get("timeout", 0) + 15) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        resp = json.loads(e.read().decode("utf-8", "ignore") or "{}")
    if not resp.get("ok"):
        raise RuntimeError(f"{metodo}: {resp.get('description')}")
    return resp["result"]


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
def banco():
    """Abre o SQLite e garante que as tabelas existem."""
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA.read_text(encoding="utf-8"))
    con.commit()
    return con


def ler_estado(con, chave, padrao=None):
    linha = con.execute("SELECT valor FROM estado WHERE chave = ?", (chave,)).fetchone()
    return linha["valor"] if linha else padrao


def gravar_estado(con, chave, valor):
    con.execute("INSERT INTO estado (chave, valor) VALUES (?, ?)"
                " ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (chave, str(valor)))
    con.commit()


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------
def teclado(card_id, acoes, links):
    """Monta os botões do card. Cada botão carrega "acao:id_do_card"."""
    botoes = [{"text": ROTULOS.get(a, a.capitalize()), "callback_data": f"{a}:{card_id}"}
              for a in acoes]
    largura = 2 if len(botoes) > 3 else 3  # 4 botões numa linha ficam espremidos no celular
    linhas = [botoes[i:i + largura] for i in range(0, len(botoes), largura)]
    for rotulo, url in links:
        linhas.append([{"text": rotulo, "url": url}])
    return {"inline_keyboard": linhas}


def mandar_card(card, con=None):
    """Grava o card no banco e manda para o Telegram. Devolve o id do card.

    card = {"tipo", "ref", "titulo", "corpo", "copiar", "links": [[rotulo, url]], "acoes": [...]}
    "copiar" vai num bloco que, no celular, se copia com um toque.
    """
    con = con or banco()
    partes = [f"<b>{html.escape(card['titulo'])}</b>"]
    if card.get("corpo"):
        partes.append(html.escape(card["corpo"]))
    if card.get("copiar"):
        partes.append(f"<pre>{html.escape(card['copiar'])}</pre>")
    texto = "\n\n".join(partes)
    card_id = con.execute(
        "INSERT INTO cards (tipo, ref, texto, criado_em) VALUES (?, ?, ?, ?)",
        (card.get("tipo", "geral"), card.get("ref"), texto, agora())).lastrowid
    acoes = card.get("acoes", ["aprovar", "ajustar", "descartar"])
    if modo_demo():
        texto = f"<b>[card #{card_id}]</b> " + texto
    msg = api("sendMessage", chat_id=chat_id(), text=texto, parse_mode="HTML",
              disable_web_page_preview=True,
              reply_markup=teclado(card_id, acoes, card.get("links", [])))
    con.execute("UPDATE cards SET msg_id = ? WHERE id = ?", (msg["message_id"], card_id))
    con.commit()
    log(f"card {card_id} enviado ({card.get('tipo')})")
    return card_id


def sincronizar(con, card_id):
    """Leva a decisão de um card (ref "msg:N") até a mensagem N e o lead dela.

    É aqui que mora a automação do funil:
      Enviei na dm1  -> lead vira "enviado" e o fu1 é agendado para daqui a 3 dias
      Enviei no fu1  -> fu2 agendado para mais 4 dias
      Enviei no fu2  -> para de insistir
      Descartar dm1  -> lead descartado
      Pular          -> a mensagem volta para o próximo lote
    Pode rodar duas vezes sem estragar nada (é idempotente).
    """
    card = con.execute("SELECT ref, status FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not card or not (card["ref"] or "").startswith("msg:"):
        return
    m = con.execute("SELECT * FROM mensagens WHERE id = ?", (int(card["ref"][4:]),)).fetchone()
    alvo = CARD_PARA_MSG.get(card["status"])
    if not m or not alvo or m["status"] == alvo:
        return
    lead_id, tipo, dia = m["lead_id"], m["tipo"], hoje()
    if alvo == "enviado":
        con.execute("UPDATE mensagens SET status = 'enviado', enviado_em = ? WHERE id = ?",
                    (agora(), m["id"]))
        if tipo in SEGUINTE:
            passo, dias = SEGUINTE[tipo]
            con.execute(
                "UPDATE leads SET estagio = CASE WHEN estagio IN ('novo', 'qualificado', 'rascunho')"
                " THEN 'enviado' ELSE estagio END, proximo_passo = ?, proximo_em = ?,"
                " atualizado_em = ? WHERE id = ? AND estagio IN ('novo', 'qualificado', 'rascunho', 'enviado')",
                (passo, (dia + timedelta(days=dias)).isoformat(), agora(), lead_id))
        elif tipo == "fu2":
            con.execute("UPDATE leads SET proximo_passo = NULL, proximo_em = NULL, atualizado_em = ?"
                        " WHERE id = ? AND estagio = 'enviado'", (agora(), lead_id))
        elif tipo in DEPOIS_DA_CONVERSA:
            estagio, passo = DEPOIS_DA_CONVERSA[tipo]
            nova = con.execute("SELECT 1 FROM mensagens WHERE lead_id = ? AND tipo = 'recebida'"
                               " AND id > ?", (lead_id, m["id"])).fetchone()
            con.execute(
                "UPDATE leads SET estagio = CASE WHEN ? IS NOT NULL AND estagio = 'respondeu'"
                " THEN ? ELSE estagio END, proximo_passo = CASE WHEN ? THEN proximo_passo"
                " WHEN ? IS NOT NULL THEN ? WHEN proximo_passo = 'responder' THEN NULL"
                " ELSE proximo_passo END, atualizado_em = ? WHERE id = ?",
                (estagio, estagio, 1 if nova else 0, passo, passo, agora(), lead_id))
    elif alvo == "descartado":
        con.execute("UPDATE mensagens SET status = 'descartado' WHERE id = ?", (m["id"],))
        if tipo == "dm1":
            con.execute("UPDATE leads SET estagio = 'descartado', proximo_passo = NULL,"
                        " proximo_em = NULL, atualizado_em = ? WHERE id = ?", (agora(), lead_id))
        elif tipo in ("fu1", "fu2"):
            con.execute("UPDATE leads SET proximo_passo = NULL, proximo_em = NULL, atualizado_em = ?"
                        " WHERE id = ?", (agora(), lead_id))
    elif alvo == "rascunho":
        con.execute("UPDATE mensagens SET status = 'rascunho', card_id = NULL WHERE id = ?", (m["id"],))
    else:  # aprovada, ajustar
        con.execute("UPDATE mensagens SET status = ? WHERE id = ?", (alvo, m["id"]))
    con.commit()
    log(f"msg {m['id']} ({tipo}) -> {alvo}")


def decidir(con, card_id, acao, nota=None):
    """Registra o botão apertado num card (e a nota, se houver) e propaga a decisão.

    É a mesma função usada pelo Telegram de verdade e pela demo.
    """
    status = STATUS[acao]
    con.execute("UPDATE cards SET status = ?, decidido_em = ?,"
                " nota = CASE WHEN ? IS NULL THEN nota ELSE COALESCE(nota || char(10), '') || ? END"
                " WHERE id = ?", (status, agora(), nota, nota, card_id))
    con.commit()
    sincronizar(con, card_id)
    log(f"card {card_id}: {status}")
    return status


# ---------------------------------------------------------------------------
# O que chega do Telegram
# ---------------------------------------------------------------------------
def tratar_botao(con, cb, meu_chat):
    if cb["from"]["id"] != meu_chat:
        return  # só o operador pareado pode decidir
    dado = cb.get("data", "")
    if dado == "noop":
        api("answerCallbackQuery", callback_query_id=cb["id"])
        return
    acao, _, card_id = dado.partition(":")
    if acao not in STATUS or not card_id.isdigit():
        api("answerCallbackQuery", callback_query_id=cb["id"], text="Botão desconhecido")
        return
    status = decidir(con, int(card_id), acao)
    aviso = f"{status.capitalize()} às {datetime.now():%H:%M}"
    api("answerCallbackQuery", callback_query_id=cb["id"], text=aviso)
    rotulo = "Ajustar: responda este card com a nota" if acao == "ajustar" else aviso
    msg = cb.get("message")
    if msg:  # troca os botões por um rótulo, para não apertar duas vezes
        api("editMessageReplyMarkup", chat_id=msg["chat"]["id"], message_id=msg["message_id"],
            reply_markup={"inline_keyboard": [[{"text": rotulo, "callback_data": "noop"}]]})


def comando_chat(con, texto, meu_chat):
    """Comandos com barra. Devolve True se tratou."""
    import crm
    partes = texto.split()
    cmd, arg = partes[0].lower(), (partes[1].lower() if len(partes) > 1 else "")
    if cmd == "/start":
        api("sendMessage", chat_id=meu_chat, text="Capta no ar.")
    elif cmd == "/status":
        r = crm.resumo(con)
        api("sendMessage", chat_id=meu_chat, text=(
            "Leads: " + (", ".join(f"{l['estagio']}: {l['n']}" for l in r["leads"]) or "nenhum")
            + f"\nModo: {ler_estado(con, 'modo_dm', 'revisao')}"))
    elif cmd == "/modo" and arg in ("revisao", "envio"):
        gravar_estado(con, "modo_dm", arg)
        api("sendMessage", chat_id=meu_chat, text=(
            "Modo envio: os próximos cards vêm com Enviei e Pular." if arg == "envio" else
            "Modo revisão: os próximos cards vêm com Aprovar, Ajustar e Descartar."))
    elif cmd == "/lote":
        crm.lote(con, manual=True)
    elif cmd in ("/resp", "/respondeu"):
        resto = texto.split(None, 2)
        if len(resto) < 3:
            api("sendMessage", chat_id=meu_chat, text="Use: /resp @usuario <o que o lead respondeu>")
        else:
            api("sendMessage", chat_id=meu_chat, text=crm.registrar_resposta(con, resto[1], resto[2])["texto"])
    elif cmd == "/reuniao":
        if len(partes) < 4:
            api("sendMessage", chat_id=meu_chat, text=(
                "Use: /reuniao @usuario 07/11 09:40\nLivres: " + crm.texto_horarios(crm.horarios_livres(con))))
        else:
            api("sendMessage", chat_id=meu_chat,
                text=crm.marcar_reuniao(con, partes[1], partes[2], partes[3])["texto"])
    else:
        return False
    return True


def tratar_mensagem(con, m, meu_chat):
    if m["chat"]["id"] != meu_chat:
        return
    texto = m.get("text", "")
    citada = m.get("reply_to_message")
    if citada:  # respondeu a um card: é a nota de ajuste
        linha = con.execute("SELECT id, status FROM cards WHERE msg_id = ?", (citada["message_id"],)).fetchone()
        if linha:
            if linha["status"] in ("pendente", "ajustar"):
                decidir(con, linha["id"], "ajustar", nota=texto)
            else:  # card já decidido (ex.: enviado): só guarda a nota, não reabre a mensagem
                con.execute("UPDATE cards SET nota = COALESCE(nota || char(10), '') || ? WHERE id = ?",
                            (texto, linha["id"]))
                con.commit()
            api("sendMessage", chat_id=meu_chat, text=f"Nota salva no card #{linha['id']}.")
            return
    if texto.startswith("/") and comando_chat(con, texto, meu_chat):
        return
    if texto:  # texto solto vira recado para o agente
        con.execute("INSERT INTO recados (texto, criado_em) VALUES (?, ?)", (texto, agora()))
        con.commit()
        api("sendMessage", chat_id=meu_chat, text="Recado anotado. Entra na próxima rodada.")


def relogio(con):
    """Automação por horário (sem IA): em dia útil, entre 12h e 18h, manda o lote uma vez."""
    import crm
    momento = datetime.now()
    dia = hoje().isoformat()
    if (momento.weekday() < 5 and HORA_LOTE[0] <= momento.hour < HORA_LOTE[1]
            and ler_estado(con, "lote_dia") != dia):
        gravar_estado(con, "lote_dia", dia)  # grava antes: se falhar no meio, não repete
        crm.lote(con)


def rodar():
    """Loop principal: a cada volta, confere o relógio e lê botões e mensagens novas."""
    if modo_demo():
        print("Sem TELEGRAM_TOKEN no .env: não dá para rodar o bot de verdade. Use demo/demo.py.")
        return
    trava = socket.socket()
    try:
        trava.bind(("127.0.0.1", PORTA_TRAVA))
    except OSError:
        print("Já existe um bot rodando.")
        return
    meu_chat = chat_id()
    con = banco()
    offset = int(ler_estado(con, "offset", 0))
    log("bot rodando")
    while True:
        try:
            relogio(con)
        except Exception as e:
            log(f"erro no relógio: {e}")
        try:
            updates = api("getUpdates", offset=offset, timeout=50,
                          allowed_updates=["message", "callback_query"])
        except Exception as e:
            log(f"erro getUpdates: {e}")
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            try:
                if "callback_query" in u:
                    tratar_botao(con, u["callback_query"], meu_chat)
                elif "message" in u:
                    tratar_mensagem(con, u["message"], meu_chat)
            except Exception as e:
                log(f"erro no update {u['update_id']}: {e}")
            gravar_estado(con, "offset", offset)


def parear():
    """Descobre o chat do operador: ele manda /start ao bot e este comando grava o id."""
    updates = api("getUpdates", timeout=0)
    starts = [u["message"] for u in updates
              if "message" in u and u["message"].get("text", "").startswith("/start")
              and u["message"]["chat"]["type"] == "private"]
    if not starts:
        print("Nenhum /start encontrado. Mande /start para o bot e rode de novo.")
        return
    chat = starts[-1]["chat"]
    gravar_env("TELEGRAM_CHAT_ID", str(chat["id"]))
    api("sendMessage", chat_id=chat["id"], text="Pareado. Daqui em diante só respondo a este chat.")
    print("Pareado.")


def teste():
    return mandar_card({
        "tipo": "teste", "titulo": "Card de teste do Capta",
        "corpo": "Toque num botão: a escolha fica gravada no banco.",
        "copiar": "Texto de exemplo. Um toque aqui copia tudo.",
    })


if __name__ == "__main__":
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(RAIZ / "capta"))
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "parear":
        parear()
    elif cmd == "rodar":
        rodar()
    elif cmd == "card":
        print(mandar_card(json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))))
    elif cmd == "teste":
        print(teste())
    else:
        print(__doc__)
