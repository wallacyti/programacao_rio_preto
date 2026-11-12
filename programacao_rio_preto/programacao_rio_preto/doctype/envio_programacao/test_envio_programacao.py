import frappe
from frappe.tests import IntegrationTestCase

from programacao_rio_preto import fluxo


def _cadastros():
	for doctype, nome in (("Cliente Programacao", "_TESTE CLIENTE"), ("Programa TV", "_TESTE PROGRAMA")):
		if not frappe.db.exists(doctype, nome):
			frappe.get_doc({"doctype": doctype, "nome": nome}).insert()


def _novo(**kw):
	_cadastros()
	doc = frappe.get_doc(
		{
			"doctype": "Envio Programacao",
			"cliente": "_TESTE CLIENTE",
			"programa": "_TESTE PROGRAMA",
			"data_hora_exibicao": "2026-11-15 20:30:00",
			"retranca": "TESTE_0001_151126_DOM_BL1.mxf",
			**kw,
		}
	).insert()
	return doc


def _mover(doc, etapa):
	doc.reload()
	doc.etapa = etapa
	doc.save()
	return doc


class TestEnvioProgramacao(IntegrationTestCase):
	def test_nasce_na_primeira_etapa_com_historico(self):
		doc = _novo(etapa=fluxo.EXIBIDO)
		self.assertEqual(doc.etapa, fluxo.AGUARDANDO_ENTREGA)
		self.assertEqual(doc.titulo, "_TESTE PROGRAMA")
		self.assertEqual(str(doc.filtro_data), "2026-11-15")
		self.assertEqual(len(doc.historico), 1)
		self.assertEqual(doc.historico[0].etapa, fluxo.AGUARDANDO_ENTREGA)

	def test_caminho_feliz_ate_exibido(self):
		doc = _novo()
		_mover(doc, fluxo.PROGRAMAS_RECEBIDOS)
		doc.recebido_com_erro = "Não"
		doc.save()
		_mover(doc, fluxo.ENVIADO_VIZ_ONE)
		_mover(doc, fluxo.ENVIADO_PROGRAMACAO)
		doc.recebido_master_com_erro = "Não"
		doc.save()
		_mover(doc, fluxo.EXIBIDO)
		self.assertEqual(
			[h.etapa for h in doc.historico],
			[
				fluxo.AGUARDANDO_ENTREGA,
				fluxo.PROGRAMAS_RECEBIDOS,
				fluxo.ENVIADO_VIZ_ONE,
				fluxo.ENVIADO_PROGRAMACAO,
				fluxo.EXIBIDO,
			],
		)
		self.assertTrue(all(h.saida for h in doc.historico[:-1]))
		self.assertFalse(doc.historico[-1].saida)
		self.assertIn("Recebido com erro: Não", doc.historico[1].resumo)

	def test_conferencia_obrigatoria_para_sair_de_programas_recebidos(self):
		doc = _novo()
		_mover(doc, fluxo.PROGRAMAS_RECEBIDOS)
		doc.etapa = fluxo.ENVIADO_VIZ_ONE
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_voltar_nao_exige_conferencia(self):
		doc = _novo()
		_mover(doc, fluxo.PROGRAMAS_RECEBIDOS)
		_mover(doc, fluxo.AGUARDANDO_ENTREGA)
		self.assertEqual(doc.etapa, fluxo.AGUARDANDO_ENTREGA)

	def test_caminho_nao_permitido(self):
		doc = _novo()
		doc.etapa = fluxo.EXIBIDO
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_devolvido_vai_para_aguardando_reenvio(self):
		doc = _novo()
		_mover(doc, fluxo.PROGRAMAS_RECEBIDOS)
		doc.recebido_com_erro = "Sim"
		doc.prob_audio = 1
		doc.acao_tomada = "Devolvido para o cliente reenviar"
		doc.save()
		doc.etapa = fluxo.ENVIADO_VIZ_ONE
		self.assertRaises(frappe.ValidationError, doc.save)
		_mover(doc, fluxo.AGUARDANDO_REENVIO)
		self.assertIn("Problemas: Áudio", doc.historico[-2].resumo)

	def test_erro_exige_problema_e_acao(self):
		doc = _novo()
		_mover(doc, fluxo.PROGRAMAS_RECEBIDOS)
		doc.recebido_com_erro = "Sim"
		doc.save()
		doc.etapa = fluxo.REEDICAO
		self.assertRaises(frappe.ValidationError, doc.save)
		doc.reload()
		doc.prob_video = 1
		doc.acao_tomada = "Corrigido em Rio Preto"
		doc.save()
		_mover(doc, fluxo.REEDICAO)
		_mover(doc, fluxo.ENVIADO_PROGRAMACAO)

	def test_ao_vivo_pula_recebimento(self):
		doc = _novo()
		doc.etapa = fluxo.ENVIADO_PROGRAMACAO
		self.assertRaises(frappe.ValidationError, doc.save)
		ao_vivo = _novo(ao_vivo=1)
		_mover(ao_vivo, fluxo.ENVIADO_PROGRAMACAO)
		self.assertEqual(ao_vivo.etapa, fluxo.ENVIADO_PROGRAMACAO)

	def test_exibido_exige_conferencia_no_master(self):
		doc = _novo(ao_vivo=1)
		_mover(doc, fluxo.ENVIADO_PROGRAMACAO)
		doc.etapa = fluxo.EXIBIDO
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_mover_pela_api(self):
		doc = _novo()
		opcoes = fluxo.opcoes_de_movimento(doc.name)
		self.assertEqual([o["etapa"] for o in opcoes], fluxo.destinos(fluxo.AGUARDANDO_ENTREGA))
		fluxo.mover(doc.name, fluxo.PROGRAMAS_RECEBIDOS)
		self.assertEqual(frappe.db.get_value("Envio Programacao", doc.name, "etapa"), fluxo.PROGRAMAS_RECEBIDOS)

	def test_kanban_drag(self):
		"""O Kanban do Frappe grava a coluna com frappe.set_value: as regras precisam valer ali também."""
		from frappe.desk.doctype.kanban_board.kanban_board import update_order_for_single_card

		doc = _novo()
		update_order_for_single_card(
			"Programação Rio Preto", doc.name, fluxo.AGUARDANDO_ENTREGA, fluxo.PROGRAMAS_RECEBIDOS, 0, 0
		)
		self.assertEqual(frappe.db.get_value("Envio Programacao", doc.name, "etapa"), fluxo.PROGRAMAS_RECEBIDOS)
		self.assertRaises(
			frappe.ValidationError,
			update_order_for_single_card,
			"Programação Rio Preto",
			doc.name,
			fluxo.PROGRAMAS_RECEBIDOS,
			fluxo.EXIBIDO,
			0,
			0,
		)
