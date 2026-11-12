"""Instalação e manutenção: papéis, Kanban, contadores e dados iniciais.

Tudo aqui é idempotente: pode rodar em todo `bench migrate` sem duplicar nada
e sem desfazer ajustes feitos pela equipe (colunas extras, campos do card etc.).
"""

import json
import os

import frappe

from programacao_rio_preto import fluxo

MODULO = "Programacao Rio Preto"
KANBAN = "Programação Rio Preto"
PAPEL_USUARIO = "Programação RP - Usuário"
PAPEL_GESTOR = "Programação RP - Gestor"
PAPEIS = (PAPEL_USUARIO, PAPEL_GESTOR)


def after_install():
	garantir_papeis()
	carregar_dados_iniciais()
	after_migrate()


def after_migrate():
	garantir_papeis()
	garantir_kanban()
	garantir_contadores()


def tem_acesso():
	"""Mostra o ícone do app na tela inicial só para quem usa o módulo."""
	roles = set(frappe.get_roles())
	return bool(roles & {*PAPEIS, "System Manager"})


# ------------------------------------------------------------------ papéis
def garantir_papeis():
	for papel in PAPEIS:
		if not frappe.db.exists("Role", papel):
			frappe.get_doc({"doctype": "Role", "role_name": papel, "desk_access": 1}).insert(
				ignore_permissions=True
			)


# ------------------------------------------------------------------ dados
def carregar_dados_iniciais():
	"""Clientes e programas vistos nos prints do Pipefy (lista parcial).

	Pode ser chamado de novo a qualquer momento; só cria o que falta:
	bench --site SITE execute programacao_rio_preto.instalacao.carregar_dados_iniciais
	"""
	caminho = os.path.join(os.path.dirname(__file__), "dados_iniciais.json")
	with open(caminho, encoding="utf-8") as f:
		dados = json.load(f)

	criados = {"Cliente Programacao": 0, "Programa TV": 0}
	for doctype, chave in (("Cliente Programacao", "clientes"), ("Programa TV", "programas")):
		for nome in dados.get(chave, []):
			if not frappe.db.exists(doctype, nome):
				frappe.get_doc({"doctype": doctype, "nome": nome, "ativo": 1}).insert(ignore_permissions=True)
				criados[doctype] += 1
	frappe.db.commit()
	return criados


# ------------------------------------------------------------------ kanban
def garantir_kanban():
	"""Cria o quadro Kanban com as 7 fases do Pipefy, na ordem certa.

	Se o quadro já existe, só acrescenta colunas que estiverem faltando.
	"""
	if frappe.db.exists("Kanban Board", KANBAN):
		board = frappe.get_doc("Kanban Board", KANBAN)
		existentes = {c.column_name for c in board.columns}
		faltando = [e for e in fluxo.ETAPAS if e not in existentes]
		if not faltando:
			return
		for etapa in faltando:
			board.append("columns", {"column_name": etapa, "status": "Active", "indicator": fluxo.cor(etapa)})
		board.save(ignore_permissions=True)
		return

	board = frappe.new_doc("Kanban Board")
	board.update(
		{
			"kanban_board_name": KANBAN,
			"reference_doctype": "Envio Programacao",
			"field_name": "etapa",
			"private": 0,
			"show_labels": 1,
			"show_assigned_to": 1,
			"show_tags_on_card": 1,
			"is_standard": "No",
			"fields": json.dumps(["cliente", "data_hora_exibicao", "retranca"]),
		}
	)
	for etapa in fluxo.ETAPAS:
		board.append("columns", {"column_name": etapa, "status": "Active", "indicator": fluxo.cor(etapa)})

	meta = frappe.get_meta("Kanban Board")
	if meta.has_field("card_fields"):
		for campo in ("cliente", "data_hora_exibicao", "retranca"):
			board.append("card_fields", {"fieldname": campo})
	if meta.has_field("title_field"):
		board.title_field = "titulo"
	if meta.has_field("use_kanban_v2"):
		board.use_kanban_v2 = 1

	board.insert(ignore_permissions=True)
	# O before_insert do Kanban pode sobrescrever o título; garante o nome do programa no card.
	if meta.has_field("title_field") and board.title_field != "titulo":
		board.db_set("title_field", "titulo")


# ------------------------------------------------------------------ contadores
def nome_contador(etapa):
	return f"PRP - {etapa}"


def garantir_contadores():
	"""Um contador (Number Card) por etapa, usado na área de trabalho do módulo."""
	cores = {
		"Red": "#E03636",
		"Pink": "#E34AA6",
		"Yellow": "#D9A400",
		"Orange": "#F2711C",
		"Purple": "#8B5CF6",
		"Blue": "#2F80ED",
		"Green": "#29A745",
	}
	for etapa in fluxo.ETAPAS:
		nome = nome_contador(etapa)
		if frappe.db.exists("Number Card", nome):
			continue
		card = frappe.get_doc(
			{
				"doctype": "Number Card",
				"name": nome,
				"label": etapa,
				"type": "Document Type",
				"document_type": "Envio Programacao",
				"function": "Count",
				"filters_json": json.dumps([["Envio Programacao", "etapa", "=", etapa, False]]),
				"is_public": 1,
				"is_standard": 0,
				"module": MODULO,
				"color": cores.get(fluxo.cor(etapa)),
				"show_percentage_stats": 0,
			}
		)
		card.flags.ignore_mandatory = True
		card.insert(ignore_permissions=True, set_name=nome)
