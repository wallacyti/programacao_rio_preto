"""Fases do processo PROGRAMAÇÃO_RIO PRETO e regras de movimentação.

Este é o único lugar onde as etapas e os caminhos permitidos são definidos.
Para mudar o fluxo, altere TRANSICOES e/ou REQUISITOS e rode `bench migrate`
(o Kanban é recriado/atualizado no after_migrate).

Origem de cada regra (análise dos prints do Pipefy, 12/11/2026):
  [PRINT]     visto nos botões "Mover card para fase" do Pipefy
  [HIPOTESE]  não visível nos prints; inferido do fluxo. Confirmar com a equipe.
"""

import frappe
from frappe import _

AGUARDANDO_ENTREGA = "Aguardando Entrega"
AGUARDANDO_REENVIO = "Aguardando Reenvio"
PROGRAMAS_RECEBIDOS = "Programas Recebidos"
REEDICAO = "Reedição"
ENVIADO_VIZ_ONE = "Enviado para o VIZ One"
ENVIADO_PROGRAMACAO = "Enviado Programação"
EXIBIDO = "Exibido"

ETAPAS = [
	AGUARDANDO_ENTREGA,
	AGUARDANDO_REENVIO,
	PROGRAMAS_RECEBIDOS,
	REEDICAO,
	ENVIADO_VIZ_ONE,
	ENVIADO_PROGRAMACAO,
	EXIBIDO,
]
ETAPA_INICIAL = AGUARDANDO_ENTREGA
ETAPA_FINAL = EXIBIDO

# Cor de cada etapa (Kanban, lista e formulário) — próximas às do Pipefy.
CORES = {
	AGUARDANDO_ENTREGA: "Red",
	AGUARDANDO_REENVIO: "Pink",
	PROGRAMAS_RECEBIDOS: "Yellow",
	REEDICAO: "Orange",
	ENVIADO_VIZ_ONE: "Purple",
	ENVIADO_PROGRAMACAO: "Blue",
	EXIBIDO: "Green",
}

# destino -> origem: caminhos permitidos
TRANSICOES = {
	AGUARDANDO_ENTREGA: [
		PROGRAMAS_RECEBIDOS,  # [PRINT]
		ENVIADO_PROGRAMACAO,  # [HIPOTESE] programas AO VIVO (histórico do card "Escolhas da Vida")
	],
	AGUARDANDO_REENVIO: [
		PROGRAMAS_RECEBIDOS,  # [HIPOTESE] cliente reenviou o material
	],
	PROGRAMAS_RECEBIDOS: [
		ENVIADO_VIZ_ONE,  # [PRINT]
		AGUARDANDO_ENTREGA,  # [PRINT] voltar
		AGUARDANDO_REENVIO,  # [HIPOTESE] ação "Devolvido para o cliente reenviar"
		REEDICAO,  # [HIPOTESE] ação "Corrigido em Rio Preto"
	],
	REEDICAO: [
		ENVIADO_VIZ_ONE,  # [HIPOTESE]
		ENVIADO_PROGRAMACAO,  # [HIPOTESE] (Enviado Programação volta para Reedição no print)
	],
	ENVIADO_VIZ_ONE: [
		ENVIADO_PROGRAMACAO,  # [HIPOTESE]
		PROGRAMAS_RECEBIDOS,  # [HIPOTESE] voltar
	],
	ENVIADO_PROGRAMACAO: [
		EXIBIDO,  # [PRINT]
		REEDICAO,  # [PRINT] voltar
	],
	EXIBIDO: [
		ENVIADO_PROGRAMACAO,  # [PRINT] voltar
	],
}

PROBLEMAS = {
	"prob_video": "Vídeo",
	"prob_audio": "Áudio",
	"prob_edicao": "Edição",
	"prob_claquete": "Claquete",
	"prob_retranca": "Retranca",
	"prob_conteudo": "Conteúdo",
}


def cor(etapa):
	return CORES.get(etapa, "Gray")


def destinos(origem):
	return TRANSICOES.get(origem, [])


def eh_volta(origem, destino):
	return ETAPAS.index(destino) < ETAPAS.index(origem)


def problemas_marcados(doc):
	return [rotulo for campo, rotulo in PROBLEMAS.items() if doc.get(campo)]


def pendencias(doc, origem, destino):
	"""Lista do que falta preencher para mover `doc` de `origem` para `destino`.

	Lista vazia = pode mover.
	"""
	faltando = []

	if destino not in destinos(origem):
		return [_("Não é possível mover de \"{0}\" para \"{1}\".").format(origem, destino)]

	# Sair de Programas Recebidos para frente exige a conferência (campo obrigatório no Pipefy).
	if origem == PROGRAMAS_RECEBIDOS and not eh_volta(origem, destino):
		if not doc.recebido_com_erro:
			faltando.append(_("Responda \"O programa foi recebido com algum erro?\""))
		elif doc.recebido_com_erro == "Sim":
			# [HIPOTESE] com erro, registrar o problema e a ação tomada
			if not problemas_marcados(doc):
				faltando.append(_("Marque quais problemas foram encontrados"))
			if not doc.acao_tomada:
				faltando.append(_("Informe qual ação foi tomada"))

		if destino == AGUARDANDO_REENVIO and (
			doc.recebido_com_erro != "Sim" or doc.acao_tomada != "Devolvido para o cliente reenviar"
		):
			faltando.append(
				_("Para ir a Aguardando Reenvio, a ação tomada deve ser \"Devolvido para o cliente reenviar\"")
			)
		if destino == REEDICAO and (doc.recebido_com_erro != "Sim" or doc.acao_tomada != "Corrigido em Rio Preto"):
			faltando.append(_("Para ir a Reedição, a ação tomada deve ser \"Corrigido em Rio Preto\""))
		if destino == ENVIADO_VIZ_ONE and doc.acao_tomada == "Devolvido para o cliente reenviar":
			faltando.append(_("O material foi devolvido ao cliente: mova para Aguardando Reenvio"))

	# Programa AO VIVO pode ir direto de Aguardando Entrega para Enviado Programação.
	if origem == AGUARDANDO_ENTREGA and destino == ENVIADO_PROGRAMACAO and not doc.ao_vivo:
		faltando.append(_("Só programas marcados como AO VIVO vão direto para Enviado Programação"))

	# Chegar em Exibido exige a conferência no Master (obrigatória no Pipefy).
	if origem == ENVIADO_PROGRAMACAO and destino == EXIBIDO and not doc.recebido_master_com_erro:
		faltando.append(_("Responda \"O programa foi recebido no Master com algum erro?\""))

	return faltando


def resumo_da_etapa(doc, etapa):
	"""Texto guardado no histórico quando o card sai de uma etapa (para não perder respostas)."""
	partes = []
	if etapa == PROGRAMAS_RECEBIDOS and doc.recebido_com_erro:
		partes.append(_("Recebido com erro: {0}").format(doc.recebido_com_erro))
		if doc.recebido_com_erro == "Sim":
			if problemas_marcados(doc):
				partes.append(_("Problemas: {0}").format(", ".join(problemas_marcados(doc))))
			if doc.acao_tomada:
				partes.append(_("Ação: {0}").format(doc.acao_tomada))
		if doc.obs_recebimento:
			partes.append(_("Obs.: {0}").format(doc.obs_recebimento))
	elif etapa == ENVIADO_PROGRAMACAO and doc.recebido_master_com_erro:
		partes.append(_("Erro no Master: {0}").format(doc.recebido_master_com_erro))
	elif etapa == EXIBIDO and doc.erro_exibicao:
		partes.append(_("Erro de exibição: {0}").format(doc.erro_exibicao))
		if doc.descricao_erro_exibicao:
			partes.append(doc.descricao_erro_exibicao)
	return " | ".join(partes)


@frappe.whitelist()
def opcoes_de_movimento(name):
	"""Botões "Mover para" do formulário."""
	doc = frappe.get_doc("Envio Programacao", name)
	doc.check_permission("read")
	return [
		{"etapa": d, "cor": cor(d), "volta": eh_volta(doc.etapa, d), "pendencias": pendencias(doc, doc.etapa, d)}
		for d in destinos(doc.etapa)
	]


@frappe.whitelist(methods=["POST"])
def mover(name, etapa):
	doc = frappe.get_doc("Envio Programacao", name)
	doc.check_permission("write")
	doc.etapa = etapa
	doc.save()
	return {"etapa": doc.etapa}

