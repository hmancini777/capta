"""Testes da automação do Capta (a parte sem IA).

Roda com:  python -m unittest discover testes

Cada teste cria um banco temporário em modo demo, então não precisa de
Telegram nem de internet. Eles provam as regras que o sistema promete:
nada duplicado, follow-up no dia certo, cancelamento quando o lead responde.
"""
import os
import pathlib
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "capta"))


def lead(nome, ig, pontos=7):
    return {"nome": nome, "instagram": ig, "pontos": pontos,
            "mensagem": {"canal": "instagram", "texto": f"Olá, {nome}. Posso te mandar?"}}


class FluxoTeste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="capta-teste-")
        os.environ.update({"CAPTA_DEMO": "1", "CAPTA_HOJE": "2026-11-23",
                           "CAPTA_BANCO": os.path.join(self.tmp, "t.sqlite"),
                           "CAPTA_LOG": os.path.join(self.tmp, "t.log"),
                           "CAPTA_ENV": os.path.join(self.tmp, "sem.env")})
        import bot
        import crm
        bot.BANCO = pathlib.Path(os.environ["CAPTA_BANCO"])
        bot.LOG = pathlib.Path(os.environ["CAPTA_LOG"])
        bot.ENV = pathlib.Path(os.environ["CAPTA_ENV"])
        bot.api = lambda metodo, **p: {"message_id": 1}  # silencia o terminal
        self.bot, self.crm = bot, crm
        self.con = bot.banco()

    def tearDown(self):
        self.con.close()

    def card_da(self, lead_id, tipo="dm1"):
        return self.con.execute("SELECT card_id FROM mensagens WHERE lead_id = ? AND tipo = ?"
                                " ORDER BY id DESC LIMIT 1", (lead_id, tipo)).fetchone()["card_id"]

    def lead_(self, lead_id):
        return self.con.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()

    def test_nao_grava_o_mesmo_instagram_duas_vezes(self):
        r = self.crm.novos_leads(self.con, [lead("A", "dra.a"), lead("A de novo", "@Dra.A"),
                                            lead("A link", "https://instagram.com/dra.a/")])
        self.assertEqual(len(r["gravados"]), 1)
        self.assertEqual(r["ja_no_crm"], ["dra.a", "dra.a"])

    def test_lote_respeita_limite_e_pontuacao(self):
        self.crm.novos_leads(self.con, [lead("Baixo", "b", 6), lead("Alto", "a", 9), lead("Medio", "m", 7)])
        self.bot.gravar_estado(self.con, "modo_dm", "envio")
        self.assertEqual(self.crm.lote(self.con, max_novas=2), 2)
        no_card = [r["nome"] for r in self.con.execute(
            "SELECT l.nome FROM mensagens m JOIN leads l ON l.id = m.lead_id"
            " WHERE m.status = 'no_card' ORDER BY m.card_id")]
        self.assertEqual(no_card, ["Alto", "Medio"])

    def test_enviei_agenda_follow_ups_no_3o_e_no_7o_dia(self):
        lid = self.crm.novos_leads(self.con, [lead("A", "a")])["gravados"][0]
        self.bot.gravar_estado(self.con, "modo_dm", "envio")
        self.crm.lote(self.con)
        self.bot.decidir(self.con, self.card_da(lid), "enviei")
        self.assertEqual((self.lead_(lid)["estagio"], self.lead_(lid)["proximo_passo"],
                          self.lead_(lid)["proximo_em"]), ("enviado", "fu1", "2026-11-26"))
        # apertar de novo não muda nada (idempotente)
        self.bot.decidir(self.con, self.card_da(lid), "enviei")
        self.assertEqual(self.lead_(lid)["proximo_em"], "2026-11-26")
        # antes do 3º dia o follow-up não aparece; no 3º dia aparece
        self.assertEqual(self.crm.pendentes(self.con)["follow_ups"], [])
        os.environ["CAPTA_HOJE"] = "2026-11-26"
        self.assertEqual(self.crm.pendentes(self.con)["follow_ups"][0]["tipo"], "fu1")
        self.crm.gravar_mensagem(self.con, lid, "fu1", "instagram", "Lembrete?")
        self.con.commit()
        self.crm.lote(self.con)
        self.bot.decidir(self.con, self.card_da(lid, "fu1"), "enviei")
        self.assertEqual((self.lead_(lid)["proximo_passo"], self.lead_(lid)["proximo_em"]),
                         ("fu2", "2026-11-30"))

    def test_resposta_cancela_follow_up_pendente(self):
        lid = self.crm.novos_leads(self.con, [lead("A", "a")])["gravados"][0]
        self.bot.gravar_estado(self.con, "modo_dm", "envio")
        self.crm.lote(self.con)
        self.bot.decidir(self.con, self.card_da(lid), "enviei")
        self.crm.gravar_mensagem(self.con, lid, "fu1", "instagram", "Lembrete?")
        self.con.commit()
        r = self.crm.registrar_resposta(self.con, "@a", "Pode mandar!")
        self.assertTrue(r["ok"])
        fu = self.con.execute("SELECT status FROM mensagens WHERE lead_id = ? AND tipo = 'fu1'", (lid,)).fetchone()
        self.assertEqual(fu["status"], "descartado")
        self.assertEqual(self.lead_(lid)["estagio"], "respondeu")
        self.assertEqual(self.crm.pendentes(self.con)["respostas"][0]["lead_id"], lid)

    def test_ajustar_guarda_a_nota_para_o_agente(self):
        lid = self.crm.novos_leads(self.con, [lead("A", "a")])["gravados"][0]
        self.crm.lote(self.con)  # modo revisão
        self.bot.decidir(self.con, self.card_da(lid), "ajustar", nota="mais curto")
        ajustar = self.crm.pendentes(self.con)["ajustar"]
        self.assertEqual((ajustar[0]["lead_id"], ajustar[0]["nota"]), (lid, "mais curto"))

    def test_descartar_tira_o_lead_do_funil(self):
        lid = self.crm.novos_leads(self.con, [lead("A", "a")])["gravados"][0]
        self.crm.lote(self.con)
        self.bot.decidir(self.con, self.card_da(lid), "descartar")
        self.assertEqual(self.lead_(lid)["estagio"], "descartado")


if __name__ == "__main__":
    unittest.main()
