import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, time_diff_in_seconds

from programacao_rio_preto import fluxo


class EnvioProgramacao(Document):
	def validate(self):
		self.titulo = self.programa
		self.filtro_data = getdate(self.data_hora_exibicao) if self.data_hora_exibicao else None
		if self.link_viz:
			self.link_viz = self.link_viz.strip()
		self._controlar_etapa()

	# ------------------------------------------------------------------ etapas
	def _controlar_etapa(self):
		importando = self.flags.importando_pipefy

		if self.is_new():
			if not importando:
				# Todo card nasce na primeira fase, como no Pipefy.
				self.etapa = fluxo.ETAPA_INICIAL
			if not self.historico:
				self._registrar_entrada(self.etapa, self.pipefy_criado_em if importando else None)
			return

		anterior = self.get_doc_before_save()
		origem = anterior.etapa if anterior else None
		if not origem or origem == self.etapa:
			return

		if not importando:
			faltando = fluxo.pendencias(self, origem, self.etapa)
			if faltando:
				frappe.throw(
					"<br>".join(["• " + f for f in faltando]),
					title=_("Não foi possível mover para {0}").format(self.etapa),
				)

		self._registrar_saida(origem)
		self._registrar_entrada(self.etapa)

	def _registrar_entrada(self, etapa, quando=None):
		quando = quando or now_datetime()
		self.etapa_desde = quando
		self.append(
			"historico",
			{"etapa": etapa, "entrada": quando, "usuario": frappe.session.user},
		)

	def _registrar_saida(self, etapa):
		agora = now_datetime()
		aberta = next((h for h in reversed(self.historico) if not h.saida), None)
		if not aberta:
			return
		aberta.saida = agora
		aberta.duracao = max(int(time_diff_in_seconds(agora, aberta.entrada)), 0) if aberta.entrada else 0
		aberta.resumo = fluxo.resumo_da_etapa(self, etapa)
