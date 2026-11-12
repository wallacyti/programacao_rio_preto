"""Importa os cards do pipe PROGRAMAÇÃO_RIO PRETO a partir da exportação do Pipefy.

Como exportar no Pipefy: Relatórios → (relatório com todos os campos e todas as
fases) → Exportar → Excel (.xlsx). CSV também é aceito.

Uso (sempre simule primeiro):

  bench --site SITE execute programacao_rio_preto.importador.importar \
      --kwargs "{'arquivo': '/caminho/export.xlsx', 'simular': 1}"

  bench --site SITE execute programacao_rio_preto.importador.importar \
      --kwargs "{'arquivo': '/caminho/export.xlsx', 'simular': 0}"

Parâmetros opcionais:
  incluir_exibidos=0   não importa os cards já exibidos (são ~42 mil)
  exibidos_desde='2026-01-01'  importa só os exibidos a partir dessa data
  limite=100           para testar com poucas linhas

- Cards já importados (mesmo ID do Pipefy) são pulados; pode rodar de novo.
- Clientes e programas que não existirem são criados.
- Os cabeçalhos são reconhecidos sem depender de acento/maiúscula.
"""

import csv
import datetime
import unicodedata

import frappe
from frappe.utils import cint, get_datetime, getdate, now_datetime

from programacao_rio_preto import fluxo


def _chave(texto):
	"""'RETRANCA/ NOME DO ARQUIVO' -> 'RETRANCANOMEDOARQUIVO'."""
	texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
	return "".join(c for c in texto.upper() if c.isalnum())


# chave normalizada do cabeçalho -> campo interno.
# Para "OBSERVACOES" (aparece duas vezes: formulário inicial e conferência),
# a 1ª ocorrência vai para observacoes e a 2ª para obs_recebimento.
CABECALHOS = {
	"ID": "pipefy_id",
	"CODIGO": "pipefy_id",
	"CARDID": "pipefy_id",
	"TITULO": "titulo",
	"TITLE": "titulo",
	"FASEATUAL": "fase",
	"CURRENTPHASE": "fase",
	"FASE": "fase",
	"PHASE": "fase",
	"CRIADOEM": "criado_em",
	"CREATEDAT": "criado_em",
	"DATADECRIACAO": "criado_em",
	"CRIADOPOR": "criado_por",
	"CREATOR": "criado_por",
	"CREATEDBY": "criado_por",
	"ETIQUETAS": "etiquetas",
	"LABELS": "etiquetas",
	"CLIENTE": "cliente",
	"PROGRAMA": "programa",
	"DATAEHORADAEXIBICAO": "data_hora_exibicao",
	"FILTRODATA": "filtro_data",
	"RETRANCANOMEDOARQUIVO": "retranca",
	"RETRANCA": "retranca",
	"LINKDOVIZ": "link_viz",
	"LINKVIZ": "link_viz",
	"OBSERVACOES": "observacoes",
	"TIPODEEXIBICAO": "tipo_exibicao",
	"OPROGRAMAFOIRECEBIDOCOMALGUMERRO": "recebido_com_erro",
	"QUAISPROBLEMASFORAMENCONTRADOS": "problemas",
	"QUALACAOFOITOMADA": "acao_tomada",
	"OPROGRAMAFOIRECEBIDONOMASTERCOMALGUMERRO": "recebido_master_com_erro",
	"PROGRAMATEVEERRODEEXIBICAO": "erro_exibicao",
	"DESCRICAODOERRO": "descricao_erro_exibicao",
}

FASES = {_chave(e): e for e in fluxo.ETAPAS}
ACOES = {
	_chave("Corrigido em Rio Preto"): "Corrigido em Rio Preto",
	_chave("Devolvido para o cliente reenviar"): "Devolvido para o cliente reenviar",
}
PROBLEMAS_POR_CHAVE = {
	"VIDEO": "prob_video",
	"AUDIO": "prob_audio",
	"EDICAO": "prob_edicao",
	"CLAQUETE": "prob_claquete",
	"RETRANCA": "prob_retranca",
	"CONTEUDO": "prob_conteudo",
}


# ------------------------------------------------------------------ leitura
def _ler_linhas(arquivo):
	if arquivo.lower().endswith((".xlsx", ".xlsm")):
		from openpyxl import load_workbook

		wb = load_workbook(arquivo, read_only=True, data_only=True)
		ws = wb.active
		linhas = ws.iter_rows(values_only=True)
		cabecalho = next(linhas)
		for linha in linhas:
			if any(v not in (None, "") for v in linha):
				yield cabecalho, linha
		wb.close()
	else:
		with open(arquivo, encoding="utf-8-sig", newline="") as f:
			amostra = f.read(4096)
			f.seek(0)
			dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
			leitor = csv.reader(f, dialeto)
			cabecalho = next(leitor)
			for linha in leitor:
				if any(v.strip() for v in linha):
					yield cabecalho, linha


def _mapear_cabecalho(cabecalho):
	"""Índice da coluna -> campo interno. Colunas desconhecidas são ignoradas."""
	mapa, vistos, ignorados = {}, {}, []
	for i, titulo in enumerate(cabecalho):
		chave = _chave(titulo)
		campo = CABECALHOS.get(chave)
		if not campo:
			if titulo:
				ignorados.append(str(titulo))
			continue
		vistos[campo] = vistos.get(campo, 0) + 1
		if campo == "observacoes" and vistos[campo] == 2:
			campo = "obs_recebimento"
		elif vistos[campo] > 1:
			continue
		mapa[i] = campo
	return mapa, ignorados


def _texto(v):
	if v is None:
		return ""
	if isinstance(v, float) and v.is_integer():
		v = int(v)
	return " ".join(str(v).split()) if not isinstance(v, str) or "\n" not in v else v.strip()


def _data_hora(v):
	if v in (None, ""):
		return None
	if isinstance(v, datetime.datetime):
		return v
	if isinstance(v, datetime.date):
		return datetime.datetime.combine(v, datetime.time())
	texto = str(v).strip()
	for formato in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%d/%m/%y %H:%M", "%d/%m/%Y, %H:%M"):
		try:
			return datetime.datetime.strptime(texto, formato)
		except ValueError:
			pass
	try:
		return get_datetime(texto.replace("T", " ").split("+")[0].split(".")[0].rstrip("Z"))
	except Exception:
		return None


def _sim_nao(v):
	k = _chave(v)
	return {"SIM": "Sim", "NAO": "Não", "YES": "Sim", "NO": "Não", "TRUE": "Sim", "FALSE": "Não"}.get(k, "")


# ------------------------------------------------------------------ conversão
def _montar(valores):
	"""Dicionário lido da planilha -> campos do Envio Programacao. Retorna (campos, avisos)."""
	avisos = []
	campos = {}

	programa = _texto(valores.get("programa")) or _texto(valores.get("titulo"))
	campos["programa"] = programa
	campos["cliente"] = _texto(valores.get("cliente")) or "OUTROS"

	fase = FASES.get(_chave(valores.get("fase")))
	if not fase:
		avisos.append(f"fase desconhecida '{valores.get('fase')}' (usando {fluxo.ETAPA_INICIAL})")
		fase = fluxo.ETAPA_INICIAL
	campos["etapa"] = fase

	exibicao = _data_hora(valores.get("data_hora_exibicao"))
	if not exibicao and valores.get("filtro_data"):
		exibicao = _data_hora(valores.get("filtro_data"))
	campos["data_hora_exibicao"] = exibicao

	campos["retranca"] = _texto(valores.get("retranca"))
	campos["link_viz"] = _texto(valores.get("link_viz"))
	campos["observacoes"] = _texto(valores.get("observacoes"))
	campos["obs_recebimento"] = _texto(valores.get("obs_recebimento"))

	tipo = _chave(valores.get("tipo_exibicao"))
	campos["ao_vivo"] = 1 if "AOVIVO" in tipo else 0
	campos["reprise"] = 1 if "REPRISE" in tipo else 0

	campos["recebido_com_erro"] = _sim_nao(valores.get("recebido_com_erro"))
	problemas = _chave(valores.get("problemas"))
	for chave, campo in PROBLEMAS_POR_CHAVE.items():
		campos[campo] = 1 if chave in problemas else 0
	campos["acao_tomada"] = ACOES.get(_chave(valores.get("acao_tomada")), "")
	campos["recebido_master_com_erro"] = _sim_nao(valores.get("recebido_master_com_erro"))
	campos["erro_exibicao"] = _sim_nao(valores.get("erro_exibicao"))
	campos["descricao_erro_exibicao"] = _texto(valores.get("descricao_erro_exibicao"))

	campos["pipefy_id"] = _texto(valores.get("pipefy_id"))
	campos["pipefy_criado_por"] = _texto(valores.get("criado_por"))
	campos["pipefy_criado_em"] = _data_hora(valores.get("criado_em"))
	return campos, avisos


def _garantir_cadastro(doctype, nome, cache, simular):
	if nome in cache:
		return False
	cache.add(nome)
	if frappe.db.exists(doctype, nome):
		return False
	if not simular:
		frappe.get_doc({"doctype": doctype, "nome": nome, "ativo": 1}).insert(ignore_permissions=True)
	return True


# ------------------------------------------------------------------ entrada
def importar(arquivo, simular=1, incluir_exibidos=1, exibidos_desde=None, limite=0):
	simular = cint(simular)
	incluir_exibidos = cint(incluir_exibidos)
	limite = cint(limite)
	desde = getdate(exibidos_desde) if exibidos_desde else None

	resultado = frappe._dict(
		simulacao=bool(simular), lidas=0, importadas=0, ja_existiam=0, puladas_exibidos=0,
		sem_programa=0, erros=0, por_etapa={}, clientes_novos=[], programas_novos=[],
		colunas_ignoradas=[], avisos=[],
	)
	ids_existentes = set(
		frappe.get_all("Envio Programacao", filters={"pipefy_id": ["is", "set"]}, pluck="pipefy_id")
	)
	cache_clientes, cache_programas = set(), set()
	mapa = None

	for cabecalho, linha in _ler_linhas(arquivo):
		if mapa is None:
			mapa, resultado.colunas_ignoradas = _mapear_cabecalho(cabecalho)
			if "programa" not in mapa.values() and "titulo" not in mapa.values():
				frappe.throw("Não encontrei a coluna PROGRAMA nem Título na planilha.")
		if limite and resultado.lidas >= limite:
			break
		resultado.lidas += 1
		valores = {campo: linha[i] for i, campo in mapa.items() if i < len(linha)}
		campos, avisos = _montar(valores)
		ref = campos["pipefy_id"] or f"linha {resultado.lidas + 1}"

		if not campos["programa"]:
			resultado.sem_programa += 1
			continue
		if campos["pipefy_id"] and campos["pipefy_id"] in ids_existentes:
			resultado.ja_existiam += 1
			continue
		if campos["etapa"] == fluxo.ETAPA_FINAL:
			exibicao = campos["data_hora_exibicao"]
			if not incluir_exibidos or (desde and (not exibicao or getdate(exibicao) < desde)):
				resultado.puladas_exibidos += 1
				continue
		if not campos["data_hora_exibicao"]:
			campos["data_hora_exibicao"] = campos["pipefy_criado_em"] or now_datetime()
			avisos.append("sem data de exibição (usada a data de criação)")

		if _garantir_cadastro("Cliente Programacao", campos["cliente"], cache_clientes, simular):
			resultado.clientes_novos.append(campos["cliente"])
		if _garantir_cadastro("Programa TV", campos["programa"], cache_programas, simular):
			resultado.programas_novos.append(campos["programa"])

		for aviso in avisos:
			if len(resultado.avisos) < 200:
				resultado.avisos.append(f"{ref}: {aviso}")

		resultado.por_etapa[campos["etapa"]] = resultado.por_etapa.get(campos["etapa"], 0) + 1
		if simular:
			resultado.importadas += 1
			continue

		frappe.db.savepoint("prp_importacao")
		try:
			doc = frappe.get_doc({"doctype": "Envio Programacao", **campos})
			doc.flags.importando_pipefy = True
			doc.insert(ignore_permissions=True, ignore_mandatory=True)
			if campos["pipefy_criado_em"]:
				doc.db_set("creation", campos["pipefy_criado_em"], update_modified=False)
			for etiqueta in [e.strip() for e in _texto(valores.get("etiquetas")).split(",") if e.strip()]:
				doc.add_tag(etiqueta)
			if campos["pipefy_id"]:
				ids_existentes.add(campos["pipefy_id"])
			resultado.importadas += 1
		except Exception as e:
			resultado.erros += 1
			if len(resultado.avisos) < 200:
				resultado.avisos.append(f"{ref}: ERRO {e}")
			frappe.db.rollback(save_point="prp_importacao")
			continue

		if resultado.importadas % 500 == 0:
			frappe.db.commit()
			print(f"... {resultado.importadas} importadas")

	if simular:
		frappe.db.rollback()
	else:
		frappe.db.commit()
	return resultado
