"""Ocorrências: materiais com erro no recebimento, no Master ou na exibição."""

import frappe
from frappe import _

from programacao_rio_preto.fluxo import PROBLEMAS

CAMPOS_ERRO = {
	"Recebimento": "recebido_com_erro",
	"Master": "recebido_master_com_erro",
	"Exibição": "erro_exibicao",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return colunas(), dados(filters)


def colunas():
	return [
		{"fieldname": "name", "label": _("Envio"), "fieldtype": "Link", "options": "Envio Programacao", "width": 140},
		{"fieldname": "programa", "label": _("Programa"), "fieldtype": "Link", "options": "Programa TV", "width": 220},
		{"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente Programacao", "width": 160},
		{"fieldname": "data_hora_exibicao", "label": _("Exibição"), "fieldtype": "Datetime", "width": 150},
		{"fieldname": "etapa", "label": _("Etapa atual"), "fieldtype": "Data", "width": 150},
		{"fieldname": "recebido_com_erro", "label": _("Erro no recebimento"), "fieldtype": "Data", "width": 90},
		{"fieldname": "problemas", "label": _("Problemas"), "fieldtype": "Data", "width": 200},
		{"fieldname": "acao_tomada", "label": _("Ação tomada"), "fieldtype": "Data", "width": 200},
		{"fieldname": "recebido_master_com_erro", "label": _("Erro no Master"), "fieldtype": "Data", "width": 90},
		{"fieldname": "erro_exibicao", "label": _("Erro de exibição"), "fieldtype": "Data", "width": 90},
		{"fieldname": "descricao_erro_exibicao", "label": _("Descrição do erro"), "fieldtype": "Data", "width": 250},
	]


def dados(filters):
	condicoes = {}
	if filters.de and filters.ate:
		condicoes["filtro_data"] = ["between", [filters.de, filters.ate]]
	elif filters.de:
		condicoes["filtro_data"] = [">=", filters.de]
	elif filters.ate:
		condicoes["filtro_data"] = ["<=", filters.ate]
	if filters.cliente:
		condicoes["cliente"] = filters.cliente
	if filters.programa:
		condicoes["programa"] = filters.programa

	ou = None
	if filters.tipo:
		condicoes[CAMPOS_ERRO[filters.tipo]] = "Sim"
	else:
		ou = {campo: "Sim" for campo in CAMPOS_ERRO.values()}

	campos = [
		"name", "programa", "cliente", "data_hora_exibicao", "etapa", "recebido_com_erro",
		"acao_tomada", "recebido_master_com_erro", "erro_exibicao", "descricao_erro_exibicao",
		*PROBLEMAS.keys(),
	]
	linhas = frappe.get_list(
		"Envio Programacao",
		filters=condicoes,
		or_filters=ou,
		fields=campos,
		order_by="data_hora_exibicao desc",
		limit_page_length=0,
	)
	for l in linhas:
		l["problemas"] = ", ".join(rotulo for campo, rotulo in PROBLEMAS.items() if l.get(campo))
	return linhas
