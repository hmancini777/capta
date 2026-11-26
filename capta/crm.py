"""CRM do Capta: leads, mensagens e o lote diário. É a "memória" que os agentes usam.

Os agentes de IA não mexem no banco direto: eles chamam estes comandos, que
validam os dados, evitam contato duplicado e mantêm o funil coerente.

USO
  python capta/crm.py pendentes              JSON com tudo que a próxima rodada do agente precisa fazer
  python capta/crm.py novos-leads <json>     grava leads novos, cada um com a 1ª mensagem rascunhada
  python capta/crm.py mensagem <json>        grava uma mensagem para um lead que já existe
  python capta/crm.py atualizar-lead <json>  completa ou descarta um lead
  python capta/crm.py recados-lidos <id...>  marca recados do operador como lidos
  python capta/crm.py lote [max]             manda agora os cards do dia (o bot faz isso sozinho às 12h)
  python capta/crm.py respostas              manda agora os cards de conversa (lead que respondeu)
  python capta/crm.py resposta-recebida <@usuario> <texto>   o mesmo que /resp no Telegram
  python capta/crm.py evento-criado <lead_id> <id_evento>    anota que a reunião já está na agenda
  python capta/crm.py resumo                 funil: quantos leads em cada estágio
  python capta/crm.py aviso <texto>          manda um aviso simples ao operador

FORMATO de novos-leads (lista):
  [{"nome": "Dra. Camila Rocha", "instagram": "dracamilarocha", "whatsapp": "11999999999",
    "bairro": "Moema", "fonte": "maps+instagram", "seguidores": 3200, "pontos": 8,
    "sinais": "por que é bom lead, com dado concreto",
    "mensagem": {"canal": "instagram", "texto": "a 1ª mensagem", "contexto": "Reel citado: ..."}}]

FORMATO de mensagem:
  {"lead_id": 12, "tipo": "fu1", "canal": "instagram", "texto": "...", "contexto": "...",
   "substitui": 34}     # substitui = id da mensagem que esta reescreve (opcional)
"""
import json
import pathlib
import re
import sys
import urllib.parse
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bot  # noqa: E402

MAX_NOVAS = 15  # limite de 1ªs mensagens por dia útil: protege a conta e a qualidade
ROTULO_TIPO = {"dm1": "Mensagem nova", "fu1": "Follow-up 1", "fu2": "Follow-up 2",
               "resposta": "Resposta", "diagnostico": "Diagnóstico"}
CONVERSA = ("resposta", "diagnostico")  # o lead já respondeu: sai na hora, sem limite diário
HORARIOS_SABADO = ("09:00", "09:40", "10:20", "11:00", "11:40")  # reuniões de 30 min
CAMPOS_LEAD = ("nome", "instagram", "whatsapp", "email", "bairro", "fonte", "sinais",
               "seguidores", "pontos", "notas", "estagio", "proximo_passo", "proximo_em", "evento")


# ---------------------------------------------------------------------------
# Limpeza de dados: o agente pode mandar "@Fulano", um link ou um número com
# traço. Aqui tudo vira um formato único, para a checagem de duplicado funcionar.
# ---------------------------------------------------------------------------
def limpar_ig(valor):
    if not valor:
        return None
    valor = valor.strip().lower()
    valor = re.sub(r"^https?://(www\.)?instagram\.com/", "", valor)
    return valor.strip("@/ ").split("/")[0].split("?")[0] or None


def limpar_wa(valor):
    if not valor:
        return None
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) in (10, 11):  # número brasileiro sem o 55
        digitos = "55" + digitos
    return digitos or None


def achar_lead(con, termo):
    """Acha um lead pelo @ do Instagram ou, se não achar, por parte do nome."""
    ig = limpar_ig(termo)
    if ig:
        achados = con.execute("SELECT * FROM leads WHERE instagram = ?", (ig,)).fetchall()
        if achados:
            return achados
    nome = termo.strip("@ ").replace(".", " ").replace("_", " ")
    return con.execute("SELECT * FROM leads WHERE nome LIKE ? AND estagio != 'descartado'"
                       " ORDER BY atualizado_em DESC", (f"%{nome}%",)).fetchall()


# ---------------------------------------------------------------------------
# Gravação (o que os agentes chamam)
# ---------------------------------------------------------------------------
def gravar_mensagem(con, lead_id, tipo, canal, texto, contexto=None, substitui=None):
    if substitui:  # a versão antiga fica guardada como "refeita", para histórico
        con.execute("UPDATE mensagens SET status = 'refeita' WHERE id = ?", (substitui,))
    if tipo == "dm1":
        con.execute("UPDATE leads SET estagio = 'rascunho', atualizado_em = ? WHERE id = ?"
                    " AND estagio IN ('novo', 'qualificado')", (bot.agora(), lead_id))
    return con.execute(
        "INSERT INTO mensagens (lead_id, tipo, canal, texto, contexto, criado_em)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (lead_id, tipo, canal, texto.strip(), contexto, bot.agora())).lastrowid


def novos_leads(con, itens):
    """Grava leads novos. Quem já está no CRM é pulado: ninguém recebe a 1ª mensagem duas vezes."""
    gravados, pulados = [], []
    for it in itens:
        ig = limpar_ig(it.get("instagram"))
        if ig and con.execute("SELECT 1 FROM leads WHERE instagram = ?", (ig,)).fetchone():
            pulados.append(ig)
            continue
        msg = it.get("mensagem")
        estagio = it.get("estagio") or ("rascunho" if msg else "qualificado")
        lead_id = con.execute(
            "INSERT INTO leads (nome, instagram, whatsapp, email, bairro, fonte, sinais,"
            " seguidores, pontos, notas, estagio, criado_em, atualizado_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (it["nome"], ig, limpar_wa(it.get("whatsapp")), it.get("email"), it.get("bairro"),
             it.get("fonte"), it.get("sinais"), it.get("seguidores"), it.get("pontos"),
             it.get("notas"), estagio, bot.agora(), bot.agora())).lastrowid
        if msg:
            gravar_mensagem(con, lead_id, "dm1", msg.get("canal", "instagram"), msg["texto"],
                            msg.get("contexto"))
        gravados.append(lead_id)
    con.commit()
    return {"gravados": gravados, "ja_no_crm": pulados}


def atualizar_lead(con, d):
    """Completa um lead (ex.: achado no Maps, analisado no Instagram depois) ou descarta."""
    campos = {k: v for k, v in d.items() if k in CAMPOS_LEAD}
    if "instagram" in campos:
        campos["instagram"] = limpar_ig(campos["instagram"])
    if "whatsapp" in campos:
        campos["whatsapp"] = limpar_wa(campos["whatsapp"])
    if campos:
        sets = ", ".join(f"{k} = ?" for k in campos)
        con.execute(f"UPDATE leads SET {sets}, atualizado_em = ? WHERE id = ?",
                    (*campos.values(), bot.agora(), d["id"]))
    if d.get("descartar"):
        con.execute("UPDATE leads SET estagio = 'descartado', notas = COALESCE(notas || char(10), '')"
                    " || ? WHERE id = ?", (f"descartado na análise: {d['descartar']}", d["id"]))
    con.commit()
    return {"atualizado": d["id"]}


def registrar_resposta(con, termo, texto, canal=None):
    """O lead respondeu: guarda o texto, cancela os follow-ups e põe o lead na fila de resposta."""
    achados = achar_lead(con, termo)
    if len(achados) > 1:
        nomes = ", ".join(f"@{l['instagram']}" if l["instagram"] else l["nome"] for l in achados[:5])
        return {"ok": False, "texto": f"Achei mais de um lead para \"{termo}\": {nomes}. Mande com o @."}
    if achados:
        lead, novo = achados[0], False
    else:  # alguém que chegou sozinho (inbound): entra no CRM agora
        ig = limpar_ig(termo) if termo.startswith("@") else None
        lead_id = con.execute(
            "INSERT INTO leads (nome, instagram, fonte, estagio, criado_em, atualizado_em)"
            " VALUES (?, ?, 'inbound', 'respondeu', ?, ?)",
            (termo.strip("@ "), ig, bot.agora(), bot.agora())).lastrowid
        lead, novo = con.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone(), True
    lead_id = lead["id"]
    if canal is None:  # o lead responde pelo canal do último contato
        ultimo = con.execute("SELECT canal FROM mensagens WHERE lead_id = ? AND status = 'enviado'"
                             " ORDER BY id DESC LIMIT 1", (lead_id,)).fetchone()
        canal = ultimo["canal"] if ultimo else "instagram"
    con.execute("INSERT INTO mensagens (lead_id, tipo, canal, texto, status, criado_em)"
                " VALUES (?, 'recebida', ?, ?, 'recebida', ?)", (lead_id, canal, texto.strip(), bot.agora()))
    # follow-ups que ainda não saíram perdem o sentido
    caidos = con.execute("UPDATE mensagens SET status = 'descartado' WHERE lead_id = ?"
                         " AND tipo IN ('fu1', 'fu2') AND status IN ('rascunho', 'aprovada', 'no_card', 'ajustar')",
                         (lead_id,)).rowcount
    con.execute(
        "UPDATE leads SET estagio = CASE WHEN estagio IN ('novo', 'qualificado', 'rascunho', 'enviado',"
        " 'perdido') THEN 'respondeu' ELSE estagio END, proximo_passo = 'responder', proximo_em = ?,"
        " atualizado_em = ? WHERE id = ?", (bot.hoje().isoformat(), bot.agora(), lead_id))
    con.commit()
    bot.log(f"lead {lead_id} respondeu")
    quem = f"@{lead['instagram']}" if lead["instagram"] else lead["nome"]
    return {"ok": True, "lead_id": lead_id, "novo": novo, "texto": (
        f"Anotado: {quem} respondeu" + (" (lead novo, entrou no CRM)" if novo else "") + ". "
        + (f"{caidos} follow-up(s) cancelado(s). " if caidos else "")
        + "O rascunho da resposta chega na próxima rodada.")}


# ---------------------------------------------------------------------------
# Agenda de reuniões (sábado de manhã)
# ---------------------------------------------------------------------------
def proximos_sabados(dia=None, n=2):
    """Os próximos n sábados com pelo menos 2 dias de folga."""
    d = (dia or bot.hoje()) + timedelta(days=2)
    d += timedelta(days=(5 - d.weekday()) % 7)
    return [d + timedelta(days=7 * i) for i in range(n)]


def horarios_livres(con, dia=None):
    ocupados = {r[0] for r in con.execute(
        "SELECT proximo_em FROM leads WHERE estagio = 'reuniao' AND proximo_em IS NOT NULL")}
    return {s.isoformat(): [h for h in HORARIOS_SABADO if f"{s.isoformat()} {h}" not in ocupados]
            for s in proximos_sabados(dia)}


def texto_horarios(livres):
    return "; ".join(f"sáb {date.fromisoformat(d):%d/%m}: " + (", ".join(h) if h else "cheio")
                     for d, h in livres.items())


def marcar_reuniao(con, termo, dia, hora):
    """O operador confirmou a reunião (/reuniao @x 07/11 09:40)."""
    achados = achar_lead(con, termo)
    if len(achados) != 1:
        return {"ok": False, "texto": f"Não achei um lead só para \"{termo}\". Mande com o @."}
    try:
        dd, mm = (int(x) for x in dia.split("/")[:2])
        base = bot.hoje()
        quando = date(base.year, mm, dd)
        if quando < base:
            quando = date(base.year + 1, mm, dd)
        h = re.fullmatch(r"(\d{1,2})(?:[:h](\d{2})?)?", hora.strip().lower())
        hh, mi = int(h.group(1)), int(h.group(2) or 0)
        if hh > 23 or mi > 59:
            raise ValueError
    except (ValueError, AttributeError):
        return {"ok": False, "texto": "Data ou hora que não entendi. Exemplo: /reuniao @usuario 07/11 09:40"}
    chave = f"{quando.isoformat()} {hh:02d}:{mi:02d}"
    lead = achados[0]
    con.execute("UPDATE leads SET estagio = 'reuniao', proximo_passo = 'reuniao', proximo_em = ?,"
                " evento = NULL, atualizado_em = ? WHERE id = ?", (chave, bot.agora(), lead["id"]))
    con.commit()
    return {"ok": True, "texto": f"Reunião com {lead['nome']} em {quando:%d/%m} às {hh:02d}:{mi:02d}. "
                                 "O evento entra na agenda na próxima rodada."}


# ---------------------------------------------------------------------------
# Pendentes: a "pauta" que o agente recebe no começo de cada rodada
# ---------------------------------------------------------------------------
def pendentes(con):
    dia = bot.hoje().isoformat()
    q = lambda sql, *p: [dict(r) for r in con.execute(sql, p)]  # noqa: E731
    return {
        "hoje": dia,
        "modo_dm": bot.ler_estado(con, "modo_dm", "revisao"),
        # instruções livres do operador
        "recados": q("SELECT id, texto, criado_em FROM recados WHERE lido = 0 ORDER BY id"),
        # mensagens que o operador mandou reescrever, com a nota dele
        "ajustar": q(
            "SELECT m.id AS msg_id, m.lead_id, l.nome, l.instagram, m.tipo, m.canal, m.texto,"
            " c.nota FROM mensagens m JOIN leads l ON l.id = m.lead_id"
            " LEFT JOIN cards c ON c.id = m.card_id WHERE m.status = 'ajustar' ORDER BY m.id"),
        # follow-ups que venceram hoje (e ainda não foram escritos)
        "follow_ups": q(
            "SELECT l.id AS lead_id, l.nome, l.instagram, l.whatsapp, l.proximo_passo AS tipo,"
            " l.proximo_em, (SELECT texto FROM mensagens WHERE lead_id = l.id AND tipo = 'dm1'"
            " AND status = 'enviado' ORDER BY id DESC LIMIT 1) AS dm1_enviada"
            " FROM leads l WHERE l.estagio = 'enviado' AND l.proximo_passo IN ('fu1', 'fu2')"
            " AND l.proximo_em <= ? AND NOT EXISTS (SELECT 1 FROM mensagens m"
            "  WHERE m.lead_id = l.id AND m.tipo = l.proximo_passo"
            "  AND m.status IN ('rascunho', 'aprovada', 'no_card', 'enviado', 'ajustar'))", dia),
        # leads aprovados nos critérios que ainda não têm 1ª mensagem
        "qualificados_sem_dm": q(
            "SELECT id AS lead_id, nome, instagram, whatsapp, bairro, fonte, sinais, pontos"
            " FROM leads WHERE estagio = 'qualificado' ORDER BY COALESCE(pontos, 0) DESC, id"),
        # quantas 1ªs mensagens já estão prontas esperando o lote
        "estoque_dm1": con.execute(
            "SELECT COUNT(*) FROM mensagens WHERE tipo = 'dm1' AND status IN ('rascunho', 'aprovada')"
        ).fetchone()[0],
        # para o pesquisador não trazer quem já está no CRM
        "instagrams_no_crm": [r[0] for r in con.execute(
            "SELECT instagram FROM leads WHERE instagram IS NOT NULL ORDER BY instagram")],
        # leads que responderam, com a conversa inteira
        "respostas": [dict(l, conversa=q(
            "SELECT id AS msg_id, tipo, canal, status, texto, criado_em FROM mensagens"
            " WHERE lead_id = ? AND status NOT IN ('refeita', 'descartado') ORDER BY id", l["lead_id"]))
            for l in q(
            "SELECT id AS lead_id, nome, instagram, whatsapp, bairro, estagio, sinais, notas"
            " FROM leads l WHERE proximo_passo = 'responder' AND NOT EXISTS (SELECT 1 FROM mensagens m"
            "  WHERE m.lead_id = l.id AND m.tipo IN ('resposta', 'diagnostico')"
            "  AND m.status IN ('rascunho', 'aprovada', 'no_card', 'ajustar')"
            "  AND m.id > (SELECT MAX(id) FROM mensagens WHERE lead_id = l.id AND tipo = 'recebida'))"
            " ORDER BY atualizado_em")],
        "horarios_sabado": horarios_livres(con),
        "reunioes_sem_evento": q(
            "SELECT id AS lead_id, nome, instagram, whatsapp, email, proximo_em AS quando FROM leads"
            " WHERE estagio = 'reuniao' AND evento IS NULL ORDER BY proximo_em"),
    }


# ---------------------------------------------------------------------------
# Lote: transforma mensagens prontas em cards no Telegram
# ---------------------------------------------------------------------------
SELECT_MSG = ("SELECT m.*, l.nome, l.instagram, l.whatsapp, l.bairro, l.seguidores, l.pontos"
              " FROM mensagens m JOIN leads l ON l.id = m.lead_id")


def card_da_mensagem(m, i, n, modo):
    """Monta o card de uma mensagem: quem é o lead, o texto para copiar e os botões."""
    ig = m["instagram"]
    linha_lead = " · ".join(x for x in [
        f"@{ig}" if ig else None, m["bairro"],
        f"{m['seguidores']:,} seguidores".replace(",", ".") if m["seguidores"] else None,
        f"{m['pontos']}/10" if m["pontos"] is not None else None] if x)
    corpo = "\n".join(x for x in [linha_lead, m["contexto"],
                                  f"Canal: {m['canal']}" if m["canal"] != "instagram" else None] if x)
    links = []
    if m["canal"] == "whatsapp" and m["whatsapp"]:  # abre o WhatsApp com o texto já colado
        links.append(["Abrir no WhatsApp", f"https://wa.me/{m['whatsapp']}?text={urllib.parse.quote(m['texto'])}"])
    elif ig:
        links.append(["Abrir a DM", f"https://ig.me/m/{ig}"])
    if ig:
        links.append(["Ver o perfil", f"https://www.instagram.com/{ig}/"])
    titulo = f"{ROTULO_TIPO.get(m['tipo'], m['tipo'])} {i}/{n} · {m['nome']}"
    if m["tipo"] in CONVERSA:  # conversa viva: sempre com Enviei
        return {"tipo": "resposta", "ref": f"msg:{m['id']}", "titulo": titulo, "corpo": corpo,
                "copiar": m["texto"], "links": links, "acoes": ["enviei", "ajustar", "descartar"]}
    em_envio = modo == "envio"
    return {
        "tipo": ("dm" if m["tipo"] == "dm1" else "followup") if em_envio else "revisao",
        "ref": f"msg:{m['id']}", "titulo": titulo, "corpo": corpo, "copiar": m["texto"], "links": links,
        "acoes": ["enviei", "pular", "ajustar", "descartar"] if em_envio else ["aprovar", "ajustar", "descartar"],
    }


def mandar_conversa(con=None):
    """Cards de resposta e diagnóstico: saem na hora, fora do limite diário."""
    con = con or bot.banco()
    fila = con.execute(
        SELECT_MSG + f" WHERE m.status IN ('rascunho', 'aprovada') AND m.tipo IN {CONVERSA}"
        " AND l.estagio != 'descartado' ORDER BY m.lead_id, m.id").fetchall()
    if not fila:
        return 0
    bot.api("sendMessage", chat_id=bot.chat_id(),
            text=f"{len(fila)} resposta(s) para lead que respondeu. Copie, mande e toque em Enviei.")
    for i, m in enumerate(fila, 1):
        card_id = bot.mandar_card(card_da_mensagem(m, i, len(fila), "envio"), con)
        con.execute("UPDATE mensagens SET status = 'no_card', card_id = ? WHERE id = ?", (card_id, m["id"]))
        con.commit()
    return len(fila)


def lote(con=None, manual=False, max_novas=None):
    """Manda os cards do dia: respostas, depois follow-ups vencidos, depois mensagens novas.

    Modo revisão: só rascunhos, para o operador aprovar ou ajustar (não conta no limite).
    Modo envio: aprovadas e rascunhos, com Enviei/Pular, até MAX_NOVAS mensagens novas por dia.
    As de maior pontuação saem primeiro.
    """
    con = con or bot.banco()
    mandar_conversa(con)
    dia = bot.hoje().isoformat()
    limite = MAX_NOVAS if max_novas is None else max_novas
    modo = bot.ler_estado(con, "modo_dm", "revisao")
    ja_hoje = con.execute("SELECT COUNT(*) FROM cards WHERE tipo = 'dm' AND criado_em >= ?",
                          (dia,)).fetchone()[0]
    status_ok = ("rascunho", "aprovada") if modo == "envio" else ("rascunho",)
    marcas = ",".join("?" * len(status_ok))
    base = (SELECT_MSG + f" WHERE m.status IN ({marcas})"
            " AND l.estagio NOT IN ('descartado', 'perdido', 'cliente')")
    fups = con.execute(base + " AND m.tipo IN ('fu1', 'fu2') ORDER BY m.id", status_ok).fetchall()
    novas = con.execute(
        base + " AND m.tipo = 'dm1' ORDER BY (m.status = 'aprovada') DESC,"
        " COALESCE(l.pontos, 0) DESC, m.id LIMIT ?", (*status_ok, max(0, limite - ja_hoje))).fetchall()
    fila = list(fups) + list(novas)
    if not fila:
        if manual or ja_hoje == 0:
            bot.api("sendMessage", chat_id=bot.chat_id(), text=(
                "Nenhuma mensagem pronta para hoje." if ja_hoje == 0 else
                f"Lote de hoje já saiu ({ja_hoje} novas). Nada novo na fila."))
        return 0
    if modo == "envio":
        cabeca = (f"Lote de hoje: {len(novas)} novas e {len(fups)} follow-ups.\n"
                  "Toque no texto para copiar, abra a conversa, cole e envie. Depois, Enviei.")
    else:
        cabeca = (f"Revisão: {len(fila)} mensagens rascunhadas.\n"
                  "Aprovar = entra no próximo lote de envio. Ajustar = responda o card dizendo o que muda.")
    bot.api("sendMessage", chat_id=bot.chat_id(), text=cabeca)
    for i, m in enumerate(fila, 1):
        card_id = bot.mandar_card(card_da_mensagem(m, i, len(fila), modo), con)
        con.execute("UPDATE mensagens SET status = 'no_card', card_id = ? WHERE id = ?", (card_id, m["id"]))
        con.commit()
    bot.log(f"lote: {len(novas)} novas, {len(fups)} follow-ups (modo {modo})")
    return len(fila)


def resumo(con):
    """O funil: quantos leads em cada estágio e quantas mensagens em cada status."""
    linhas = con.execute("SELECT estagio, COUNT(*) AS n FROM leads GROUP BY estagio ORDER BY estagio").fetchall()
    msgs = con.execute("SELECT tipo, status, COUNT(*) AS n FROM mensagens"
                       " GROUP BY tipo, status ORDER BY tipo, status").fetchall()
    return {"leads": [dict(r) for r in linhas], "mensagens": [dict(r) for r in msgs]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    con = bot.banco()
    ler = lambda p: json.loads(pathlib.Path(p).read_text(encoding="utf-8"))  # noqa: E731
    if cmd == "pendentes":
        out = pendentes(con)
    elif cmd == "novos-leads":
        out = novos_leads(con, ler(args[1]))
    elif cmd == "mensagem":
        d = ler(args[1])
        out = {"msg_id": gravar_mensagem(con, d["lead_id"], d["tipo"], d.get("canal", "instagram"),
                                         d["texto"], d.get("contexto"), d.get("substitui"))}
        con.commit()
    elif cmd == "atualizar-lead":
        out = atualizar_lead(con, ler(args[1]))
    elif cmd == "recados-lidos":
        con.executemany("UPDATE recados SET lido = 1 WHERE id = ?", [(int(i),) for i in args[1:]])
        con.commit()
        out = {"lidos": args[1:]}
    elif cmd == "lote":
        out = {"cards": lote(con, manual=True, max_novas=int(args[1]) if len(args) > 1 else None)}
    elif cmd == "respostas":
        out = {"cards": mandar_conversa(con)}
    elif cmd == "resposta-recebida":
        out = registrar_resposta(con, args[1], " ".join(args[2:]))
    elif cmd == "evento-criado":
        con.execute("UPDATE leads SET evento = ?, atualizado_em = ? WHERE id = ?",
                    (args[2], bot.agora(), int(args[1])))
        con.commit()
        out = {"evento": args[2], "lead_id": int(args[1])}
    elif cmd == "resumo":
        out = resumo(con)
    elif cmd == "aviso":
        texto = " ".join(args[1:]).strip()
        bot.api("sendMessage", chat_id=bot.chat_id(), text=texto)
        out = {"aviso": "enviado"}
    else:
        print(__doc__)
        return
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
