"""Demonstração do Capta do começo ao fim, sem Telegram, sem internet e sem IA.

Roda com:  python demo/demo.py
(Só precisa de Python 3.10 ou mais novo. Nada para instalar.)

A demo usa um banco temporário e leads FICTÍCIOS (demo/leads-exemplo.json).
As partes que, no sistema real, são feitas por agentes de IA (pesquisar leads e
escrever mensagens) aparecem aqui como textos prontos, marcados com [AGENTE].
Os cliques do operador no Telegram aparecem como [HUMANO].
Tudo o mais é a automação de verdade, o mesmo código que roda em produção.
"""
import json
import os
import pathlib
import sys
import tempfile
from datetime import date, timedelta

# --- prepara um ambiente isolado: banco temporário e modo demo -------------
PASTA = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path(tempfile.mkdtemp(prefix="capta-demo-"))
os.environ.update({
    "CAPTA_DEMO": "1",
    "CAPTA_BANCO": str(TMP / "demo.sqlite"),
    "CAPTA_LOG": str(TMP / "demo.log"),
    "CAPTA_ENV": str(TMP / "sem.env"),
})
DIA_1 = date(2026, 11, 23)  # uma segunda-feira, para as datas da demo serem sempre as mesmas
os.environ["CAPTA_HOJE"] = DIA_1.isoformat()
sys.path.insert(0, str(PASTA.parent / "capta"))
sys.stdout.reconfigure(encoding="utf-8")

import bot  # noqa: E402
import crm  # noqa: E402

PAUSA = "--rapido" not in sys.argv


def etapa(n, titulo, explicacao):
    if PAUSA:
        input("\n(Enter para continuar) ")
    print("\n" + "=" * 70)
    print(f"ETAPA {n}. {titulo}")
    print("=" * 70)
    print(explicacao.strip())
    print()


def mudar_dia(d):
    os.environ["CAPTA_HOJE"] = d.isoformat()
    print(f"  (relógio da demo: {d:%d/%m/%Y}, {['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'][d.weekday()]})")


def funil(con):
    r = crm.resumo(con)
    print("  Funil agora: " + ", ".join(f"{l['estagio']} = {l['n']}" for l in r["leads"]))


def ultimo_card(con, msg_id):
    return con.execute("SELECT card_id FROM mensagens WHERE id = ?", (msg_id,)).fetchone()["card_id"]


con = bot.banco()
print("CAPTA · demonstração do fluxo completo")
print(f"Banco temporário: {TMP}")
mudar_dia(DIA_1)

# ---------------------------------------------------------------------------
etapa(1, "Agente Pesquisador + Agente Redator (11h)", """
No sistema real, às 11h de cada dia útil um agente de IA pesquisa clínicas no
Google Maps e no Instagram, aplica os critérios de regras/criterios-lead.md,
dá uma nota de 0 a 10 e escreve a 1ª mensagem de cada lead aprovado.
Aqui, esse trabalho vem pronto de demo/leads-exemplo.json.
Repare que o 4º lead é a mesma pessoa do 1º: o CRM recusa contato duplicado.
""")
itens = json.loads((PASTA / "leads-exemplo.json").read_text(encoding="utf-8"))
for it in itens:
    print(f"  [AGENTE] lead encontrado: {it['nome']} ({it.get('pontos')}/10) · {it['sinais'][:60]}...")
r = crm.novos_leads(con, itens)
print(f"\n  CRM gravou os leads {r['gravados']} e recusou {r['ja_no_crm']} (já estava no CRM).")
funil(con)

# ---------------------------------------------------------------------------
etapa(2, "Automação: lote das 12h em modo REVISÃO", """
Ao meio-dia o bot manda sozinho um card por mensagem para o Telegram do operador.
No modo revisão os botões são Aprovar, Ajustar e Descartar: ainda não é para
enviar, é para o humano conferir se a IA escreveu do jeito certo.
Os leads com mais pontos aparecem primeiro.
""")
crm.lote(con, manual=True)

# ---------------------------------------------------------------------------
etapa(3, "Humano no controle: o operador decide cada card", """
O operador aprova a mensagem da Dra. Camila, pede ajuste na do Dr. Rafael
(respondendo ao card com uma nota) e descarta a da clínica.
Cada botão muda o banco: a mensagem e o lead andam no funil sozinhos.
""")
msgs = {m["nome"]: m["id"] for m in con.execute(
    "SELECT m.id, l.nome FROM mensagens m JOIN leads l ON l.id = m.lead_id WHERE m.tipo = 'dm1'")}
c1 = ultimo_card(con, msgs["Dra. Camila Rocha"])
c2 = ultimo_card(con, msgs["Dr. Rafael Lima"])
c3 = ultimo_card(con, msgs["Clínica Sorriso Exemplo"])
print(f"  [HUMANO] card #{c1}: Aprovar")
bot.decidir(con, c1, "aprovar")
nota = "Tira o 'gostei', fica mais direto. E fala do paciente, não do Reel."
print(f"  [HUMANO] card #{c2}: Ajustar, com a nota: \"{nota}\"")
bot.decidir(con, c2, "ajustar", nota=nota)
print(f"  [HUMANO] card #{c3}: Descartar")
bot.decidir(con, c3, "descartar")
funil(con)

# ---------------------------------------------------------------------------
etapa(4, "Aprendizado: o agente reescreve com a nota do humano", """
Na rodada seguinte, o agente recebe a lista "ajustar" de crm.py pendentes,
com a nota do operador. Ele reescreve a mensagem e grava a nota em
regras/estilo-escrita.md, para não repetir o erro com os próximos leads.
""")
p = crm.pendentes(con)
for a in p["ajustar"]:
    print(f"  Pendente de ajuste: {a['nome']} · nota: \"{a['nota']}\"")
    novo = ("Boa tarde, Dr. Rafael, tudo certo? Me chamo Henrique e trabalho com vídeo e estratégia "
            "de Instagram para profissionais de saúde. Seu Reel sobre quanto dura um implante responde "
            "a dúvida que mais trava o paciente antes de marcar. Fiz uma análise rápida do seu perfil, "
            "com 3 pontos que seguram paciente novo e 3 ideias de vídeo. Posso te mandar?")
    crm.gravar_mensagem(con, a["lead_id"], "dm1", a["canal"], novo, substitui=a["msg_id"])
    con.commit()
    print(f"  [AGENTE] reescrita: \"{novo[:90]}...\"")
    print("  [AGENTE] regra nova em estilo-escrita.md: \"falar do paciente, não do Reel; sem 'gostei'\"")

# ---------------------------------------------------------------------------
etapa(5, "Modo ENVIO: o humano envia e aperta Enviei", """
Com os textos do jeito certo, o operador manda /modo envio no Telegram.
Agora os cards vêm com Enviei e Pular. Quem envia é sempre o humano:
copia o texto, abre a DM pelo botão e cola. O sistema nunca envia sozinho.
""")
bot.gravar_estado(con, "modo_dm", "envio")
crm.lote(con, manual=True)
for nome in ("Dra. Camila Rocha", "Dr. Rafael Lima"):
    linha = con.execute("SELECT m.card_id FROM mensagens m JOIN leads l ON l.id = m.lead_id"
                        " WHERE l.nome = ? AND m.tipo = 'dm1' AND m.status = 'no_card'", (nome,)).fetchone()
    print(f"  [HUMANO] card #{linha['card_id']} ({nome}): Enviei")
    bot.decidir(con, linha["card_id"], "enviei")
for l in con.execute("SELECT nome, estagio, proximo_passo, proximo_em FROM leads WHERE estagio = 'enviado'"):
    print(f"  Automação: {l['nome']} -> {l['estagio']}, {l['proximo_passo']} agendado para {l['proximo_em']}")
funil(con)

# ---------------------------------------------------------------------------
etapa(6, "Três dias depois: o follow-up vence sozinho", """
Ninguém precisa lembrar de cobrar. No 3º dia, o "pendentes" já traz os
follow-ups vencidos e o agente escreve um lembrete curto, que vira card.
""")
mudar_dia(DIA_1 + timedelta(days=3))
for f in crm.pendentes(con)["follow_ups"]:
    print(f"  Venceu: {f['tipo']} de {f['nome']} (agendado para {f['proximo_em']})")
    texto = (f"{f['nome'].split()[0]} {f['nome'].split()[1]}, passando aqui rapidinho: a análise do seu "
             "perfil está pronta, com 3 pontos e 3 ideias de vídeo. Posso te mandar?")
    crm.gravar_mensagem(con, f["lead_id"], f["tipo"], "instagram", texto)
    con.commit()
    print(f"  [AGENTE] escreveu: \"{texto}\"")
crm.lote(con, manual=True)

# ---------------------------------------------------------------------------
etapa(7, "O lead respondeu", """
A Dra. Camila respondeu a DM. O operador avisa o bot com
/resp @dra.camila.exemplo <o que ela escreveu>.
O follow-up dela é cancelado na hora (não faz sentido cobrar quem já respondeu)
e ela entra na fila do Agente Atendente, que escreve a resposta e o diagnóstico.
""")
r = crm.registrar_resposta(con, "@dra.camila.exemplo", "Oi Henrique! Pode mandar sim, fiquei curiosa.")
print("  Bot responde ao operador: " + r["texto"])
for lead in crm.pendentes(con)["respostas"]:
    print(f"  Na fila do Atendente: {lead['nome']} · última mensagem: \"{lead['conversa'][-1]['texto']}\"")
    crm.gravar_mensagem(con, lead["lead_id"], "resposta", "instagram",
                        "Que bom, Dra. Camila! Mando logo abaixo a análise. Depois me conta o que achou?")
    crm.gravar_mensagem(con, lead["lead_id"], "diagnostico", "instagram",
                        "Dra. Camila, fiz o diagnóstico do seu perfil. São 3 pontos que mais estão segurando "
                        "paciente hoje: 1) ... 2) ... 3) ... E aqui vão 3 roteiros prontos para gravar no "
                        "celular. (formato completo em regras/diagnostico.md)")
    con.commit()
    print("  [AGENTE] escreveu a resposta e o diagnóstico (3 travas + 3 roteiros)")
crm.mandar_conversa(con)
for linha in con.execute("SELECT card_id FROM mensagens WHERE status = 'no_card' AND tipo IN ('resposta', 'diagnostico')"):
    bot.decidir(con, linha["card_id"], "enviei")
print("  [HUMANO] enviou as duas e apertou Enviei")
funil(con)

# ---------------------------------------------------------------------------
etapa(8, "Reunião marcada", """
Ela aceitou conversar no sábado. O operador marca com /reuniao.
Na rodada seguinte, o agente cria o evento na agenda (sem convidar ninguém).
""")
print("  Horários livres: " + crm.texto_horarios(crm.horarios_livres(con)))
sab = crm.proximos_sabados()[0]
print("  " + crm.marcar_reuniao(con, "@dra.camila.exemplo", f"{sab:%d/%m}", "09:40")["texto"])
funil(con)

print("\n" + "=" * 70)
print("FIM. Resumo do que aconteceu:")
print("  - 4 leads chegaram, 1 duplicado foi barrado pelo CRM")
print("  - 3 mensagens revisadas: 1 aprovada, 1 reescrita pela nota do humano, 1 descartada")
print("  - 2 enviadas, follow-ups agendados e cobrados sozinhos no 3º dia")
print("  - 1 resposta: follow-up cancelado, diagnóstico escrito e enviado, reunião marcada")
print("Nenhuma mensagem saiu sem um humano apertar o botão.")
